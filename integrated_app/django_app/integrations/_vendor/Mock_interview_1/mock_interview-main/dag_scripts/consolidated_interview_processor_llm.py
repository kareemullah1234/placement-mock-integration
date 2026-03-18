# Consolidated Interview Processing DAG with LLM-Generated Reports
from datetime import datetime, timedelta
import json
import logging
import requests
import subprocess
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import time
import hashlib
from fpdf import FPDF

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.models import Variable
from airflow.exceptions import AirflowException

# Configuration
OPENROUTER_API_KEY = Variable.get("OPENROUTER_API_KEY", default_var="your-api-key-here")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
DATABASE_CONN_ID = "mysql_default"
EMAIL_ENABLED = Variable.get("EMAIL_ENABLED", default_var="true").lower() == "true"
REPORT_STORAGE_PATH = "/mnt/storage/reports/"
DLIB_CONTAINER_ID = "435d644fe4ed"
NAMENODE_HOST = "namenode"
NAMENODE_PORT = "9870"

# Free models available on OpenRouter
FREE_MODELS = [
    "meta-llama/llama-3.2-3b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "microsoft/phi-3-mini-128k-instruct:free"
]

# Email Configuration
EMAIL_CONFIG = {
    'smtp_server': Variable.get("EMAIL_SMTP_SERVER", default_var="smtp.gmail.com"),
    'smtp_port': int(Variable.get("EMAIL_SMTP_PORT", default_var="587")),
    'sender_email': Variable.get("EMAIL_SENDER", default_var="noreply@yourcompany.com"),
    'sender_password': Variable.get("EMAIL_PASSWORD", default_var="your-app-password"),
    'report_recipients': ['pat@datamities.com', 'nithin.manchala@rubixe.com'],
    'enable_ssl': Variable.get("EMAIL_SSL", default_var="true").lower() == "true"
}

# Ensure reports directory exists
os.makedirs(REPORT_STORAGE_PATH, exist_ok=True)

# Default args
default_args = {
    'owner': 'interview-platform',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': EMAIL_ENABLED,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=10),
    'execution_timeout': timedelta(hours=2),
}

# DAG Definition
dag = DAG(
    'consolidated_interview_processor_llm',
    default_args=default_args,
    description='Consolidated Interview Processing with LLM-Generated Reports',
    schedule_interval=timedelta(minutes=40),
    catchup=False,
    max_active_runs=1,
    tags=['interview', 'consolidated', 'llm-reports'],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Consolidated Report Generator Class
class ConsolidatedInterviewReportGenerator:
    def __init__(self):
        self.openrouter_api_key = OPENROUTER_API_KEY
        self.model = FREE_MODELS[0]
        
    def call_openrouter_llm(self, prompt, max_retries=3):
        """Call OpenRouter LLM with retry logic"""
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8080",
            "X-Title": "Interview Report Generator"
        }
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
            # Removed max_tokens to allow full context processing for large JSONs
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(OPENROUTER_BASE_URL, headers=headers, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content'].strip()
                else:
                    logger.warning(f"OpenRouter API error {response.status_code}: {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                    
            except Exception as e:
                logger.error(f"OpenRouter API call failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    
        return "Analysis unavailable due to API error."
    
    def read_session_from_hdfs(self, interview_id):
        """Read interview session JSON from HDFS"""
        try:
            list_url = f"http://{NAMENODE_HOST}:{NAMENODE_PORT}/webhdfs/v1/interview_sessions?op=LISTSTATUS"
            response = requests.get(list_url, timeout=30)
            
            if response.status_code == 200:
                files_data = response.json()
                files = files_data.get('FileStatuses', {}).get('FileStatus', [])
                
                session_file = None
                for file_info in files:
                    filename = file_info['pathSuffix']
                    if f"interview_{interview_id}" in filename and filename.endswith('.json'):
                        session_file = filename
                        break
                
                if session_file:
                    file_url = f"http://{NAMENODE_HOST}:{NAMENODE_PORT}/webhdfs/v1/interview_sessions/{session_file}?op=OPEN"
                    file_response = requests.get(file_url, timeout=60)
                    
                    if file_response.status_code == 200:
                        return file_response.json()
                        
            logger.error(f"Could not find session file for interview {interview_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error reading session from HDFS: {e}")
            return None
    
    def read_combined_analyzer_result(self, interview_id, user_id):
        """Read combined analyzer result from dlib container"""
        try:
            docker_cmd = [
                'docker', 'exec', DLIB_CONTAINER_ID,
                'bash', '-c', f'find /app -name "*combined*{user_id}*{interview_id}*.json" -o -name "*COMBINED*{user_id}*{interview_id}*.json" | head -1'
            ]
            
            result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                combined_file = result.stdout.strip()
                logger.info(f"Found combined analysis file: {combined_file}")
                
                read_cmd = ['docker', 'exec', DLIB_CONTAINER_ID, 'cat', combined_file]
                read_result = subprocess.run(read_cmd, capture_output=True, text=True, timeout=30)
                
                if read_result.returncode == 0:
                    return json.loads(read_result.stdout)
                    
            logger.warning(f"Could not find combined analysis for interview {interview_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error reading combined analyzer result: {e}")
            return None
    
    def generate_behavioral_analysis(self, combined_result):
        """Generate behavioral analysis using OpenRouter LLM"""
        try:
            if not combined_result:
                return "Behavioral analysis unavailable - no combined analysis data found."
            
            behavioral_data = {
                "video_analysis": combined_result.get("video_analysis", {}),
                "audio_analysis": combined_result.get("audio_analysis", {}),
                "cross_modal_correlation": combined_result.get("cross_modal_correlation", {}),
                "integrated_assessment": combined_result.get("integrated_assessment", {})
            }
            
            prompt = f"""You are an expert interview coach analyzing a candidate's performance in a mock interview.
You are given JSON data with body language, emotional stability, posture, eye gaze, voice confidence, and speaking style.
Your task:
- Write a single short paragraph (5-7 sentences max).
- Summarize the candidate's overall impression in terms of body language and speaking delivery.
- Briefly highlight key strengths (e.g., eye contact, positivity, posture).
- Point out 1-2 areas of improvement (e.g., speaking pace, confidence, distractions).
- Keep the tone encouraging, simple, and professional.
Here is the JSON input:
{json.dumps(behavioral_data, indent=2)}

Now, generate a short interview behavior report in one paragraph."""

            return self.call_openrouter_llm(prompt)
            
        except Exception as e:
            logger.error(f"Error generating behavioral analysis: {e}")
            return "Behavioral analysis could not be generated due to processing error."
    
    def generate_technical_analysis(self, session_data):
        """Generate technical analysis using OpenRouter LLM"""
        try:
            if not session_data or 'interview_questions' not in session_data:
                return "Technical analysis unavailable - no interview questions found."
            
            questions_data = session_data['interview_questions']
            
            prompt = f"""You are an expert technical interviewer analyzing a candidate's responses to interview questions.

Analyze the following interview questions and responses. For each question, evaluate:
1. Technical accuracy and correctness
2. Depth of knowledge demonstrated
3. Use of appropriate terminology
4. Clarity of explanation
5. Relevance to the question

Provide scores out of 10 for each question and topic area (e.g., Python, Machine Learning, Statistics).
Also provide overall scores for:
- Technical Score (0-100%)
- Communication Score (0-100%) 
- Overall Score (0-100%)

Assign letter grades:
- A (90-100%): Excellent
- B (75-89%): Very Good
- C (60-74%): Good
- D (45-59%): Satisfactory
- E (30-44%): Needs Improvement
- F (0-29%): Unsatisfactory

Format your response as a structured analysis with:
1. Overall Performance Summary (scores and grades)
2. Topic-wise Performance (score/10 and detailed feedback for each topic)
3. Soft Skills Assessment (Communication, Confidence, Relevance scores)
4. Key Strengths paragraph
5. Areas for Improvement paragraph
6. Recommended Action Plan paragraph

Here are the interview questions and responses:
{json.dumps(questions_data, indent=2)}

Generate a comprehensive technical analysis report."""

            return self.call_openrouter_llm(prompt)
            
        except Exception as e:
            logger.error(f"Error generating technical analysis: {e}")
            return "Technical analysis could not be generated due to processing error."
    
    def generate_consolidated_pdf_report(self, interview_id, student_info, behavioral_analysis, technical_analysis):
        """Generate single consolidated PDF report"""
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            
            # Header
            pdf.cell(0, 10, 'Consolidated Interview Performance Report', 0, 1, 'C')
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f"Interview ID: {interview_id} | Candidate: {student_info.get('student_name', 'N/A')}", 0, 1, 'C')
            pdf.cell(0, 5, f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
            pdf.ln(10)
            
            # Section 1: Behavioral Assessment
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, 'Behavioral Assessment', 0, 1)
            pdf.set_font("Arial", '', 11)
            pdf.ln(2)
            
            behavioral_lines = behavioral_analysis.split('. ')
            for line in behavioral_lines:
                if line.strip():
                    pdf.multi_cell(0, 6, line.strip() + ('.' if not line.endswith('.') else ''))
                    pdf.ln(2)
            pdf.ln(8)
            
            # Section 2: Technical Analysis  
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, 'Technical Skills Analysis', 0, 1)
            pdf.set_font("Arial", '', 11)
            pdf.ln(2)
            
            technical_sections = technical_analysis.split('\n\n')
            for section in technical_sections:
                if section.strip():
                    if any(keyword in section for keyword in ['Summary', 'Performance', 'Assessment', 'Strengths', 'Improvement', 'Action Plan']):
                        lines = section.split('\n')
                        if lines:
                            pdf.set_font("Arial", 'B', 12)
                            pdf.multi_cell(0, 8, lines[0])
                            pdf.ln(2)
                            
                            pdf.set_font("Arial", '', 11)
                            for line in lines[1:]:
                                if line.strip():
                                    pdf.multi_cell(0, 6, line.strip())
                                    pdf.ln(1)
                    else:
                        pdf.set_font("Arial", '', 11)
                        pdf.multi_cell(0, 6, section.strip())
                    pdf.ln(5)
            
            # Grading Methodology
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, 'Evaluation Methodology', 0, 1)
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, 'How Your Interview Was Evaluated', 0, 1)
            pdf.set_font("Arial", '', 11)
            pdf.ln(4)
            
            pdf.multi_cell(0, 6, 'Your interview performance was analyzed using advanced AI technology that evaluates both your technical knowledge and behavioral presentation.')
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, 'Technical Assessment Criteria:', 0, 1)
            pdf.set_font("Arial", '', 11)
            pdf.ln(2)
            
            criteria = [
                "Technical Accuracy: Correctness and depth of your answers",
                "Terminology Usage: Appropriate use of technical terms",
                "Clarity of Explanation: How well you communicated complex concepts",
                "Problem-solving Approach: Your methodology and reasoning",
                "Relevance: How directly you addressed each question"
            ]
            
            for criterion in criteria:
                pdf.cell(0, 6, f"• {criterion}", 0, 1)
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, 'Behavioral Assessment Criteria:', 0, 1)
            pdf.set_font("Arial", '', 11)
            pdf.ln(2)
            
            behavioral_criteria = [
                "Eye Contact and Attention: Focus and engagement during the interview",
                "Speaking Confidence: Voice clarity, pace, and conviction",
                "Body Language: Posture, gestures, and overall presentation",
                "Emotional Stability: Composure and professional demeanor",
                "Communication Style: Delivery effectiveness and articulation"
            ]
            
            for criterion in behavioral_criteria:
                pdf.cell(0, 6, f"• {criterion}", 0, 1)
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, 'Grading Scale:', 0, 1)
            pdf.set_font("Arial", '', 11)
            pdf.ln(2)
            
            grades = [
                "A (90-100%): Excellent - Outstanding performance demonstrating mastery",
                "B (75-89%): Very Good - Strong performance with minor areas for improvement", 
                "C (60-74%): Good - Solid understanding with some gaps to address",
                "D (45-59%): Satisfactory - Basic knowledge present but needs development",
                "E (30-44%): Needs Improvement - Significant gaps requiring focused study",
                "F (0-29%): Unsatisfactory - Major deficiencies requiring comprehensive review"
            ]
            
            for grade in grades:
                pdf.multi_cell(0, 6, f"• {grade}")
                pdf.ln(1)
            pdf.ln(8)
            
            # Generate unique filename
            timestamp = int(time.time())
            unique_id = hashlib.md5(f"{interview_id}_{timestamp}".encode()).hexdigest()[:8]
            filename = f"Interview_{interview_id}_{student_info.get('student_name', 'Candidate').replace(' ', '_')}_{timestamp}_{unique_id}.pdf"
            file_path = os.path.join(REPORT_STORAGE_PATH, filename)
            
            # Save PDF
            pdf.output(file_path)
            
            logger.info(f"Consolidated report saved: {file_path}")
            return file_path, filename
            
        except Exception as e:
            logger.error(f"Error generating consolidated PDF: {e}")
            return None, None

# DAG Functions
def create_processing_lock_table(mysql_hook):
    """Create processing lock table"""
    try:
        create_table_query = """
        CREATE TABLE IF NOT EXISTS interview_processing_lock (
            id INT PRIMARY KEY DEFAULT 1,
            interview_id INT,
            locked_by VARCHAR(100),
            locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            UNIQUE KEY single_lock (id)
        )
        """
        mysql_hook.run(create_table_query)
        
        # Clean up expired locks
        cleanup_query = "DELETE FROM interview_processing_lock WHERE expires_at < NOW()"
        mysql_hook.run(cleanup_query)
        
        logger.info("Processing lock table ready")
    except Exception as e:
        logger.error(f"Error creating lock table: {e}")

def acquire_processing_lock(interview_id, dag_run_id):
    """Acquire processing lock"""
    try:
        mysql_hook = MySqlHook(mysql_conn_id=DATABASE_CONN_ID)
        create_processing_lock_table(mysql_hook)
        
        expires_at = datetime.now() + timedelta(minutes=120)
        
        insert_query = """
        INSERT INTO interview_processing_lock (id, interview_id, locked_by, expires_at)
        VALUES (1, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            interview_id = VALUES(interview_id),
            locked_by = VALUES(locked_by),
            locked_at = NOW(),
            expires_at = VALUES(expires_at)
        """
        
        mysql_hook.run(insert_query, parameters=[interview_id, dag_run_id, expires_at])
        
        # Verify lock
        check_query = "SELECT locked_by FROM interview_processing_lock WHERE id = 1 AND locked_by = %s"
        result = mysql_hook.get_first(check_query, parameters=[dag_run_id])
        
        if result:
            logger.info(f"Acquired processing lock for interview {interview_id}")
            return True
        else:
            logger.warning(f"Failed to acquire processing lock for interview {interview_id}")
            return False
            
    except Exception as e:
        logger.error(f"Error acquiring processing lock: {e}")
        return False

def release_processing_lock(dag_run_id):
    """Release processing lock"""
    try:
        mysql_hook = MySqlHook(mysql_conn_id=DATABASE_CONN_ID)
        delete_query = "DELETE FROM interview_processing_lock WHERE id = 1 AND locked_by = %s"
        mysql_hook.run(delete_query, parameters=[dag_run_id])
        logger.info("Released processing lock")
        return True
    except Exception as e:
        logger.error(f"Error releasing processing lock: {e}")
        return False

def update_processing_status(interview_id, status, details=None):
    """Update processing status"""
    try:
        mysql_hook = MySqlHook(mysql_conn_id=DATABASE_CONN_ID)
        
        if 'completed' in status:
            query = """
            UPDATE interview_system_interview
            SET analysis_completed = TRUE, processing_status = %s, last_processing_update = NOW()
            WHERE id = %s
            """
        else:
            query = """
            UPDATE interview_system_interview
            SET processing_status = %s, last_processing_update = NOW()
            WHERE id = %s
            """
            
        mysql_hook.run(query, parameters=[status, interview_id])
        logger.info(f"Status updated for interview {interview_id}: {status}")
        return True
        
    except Exception as e:
        logger.error(f"Error updating status: {e}")
        return False

def send_email_with_report(student_info, report_path, report_filename):
    """Send email with consolidated report"""
    try:
        if not EMAIL_ENABLED:
            logger.info("Email disabled")
            return True
            
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = ', '.join(EMAIL_CONFIG['report_recipients'])
        msg['Subject'] = f"Interview Analysis Report - {student_info.get('student_name')} (Interview #{student_info.get('interview_id')})"
        
        html_content = f"""
        <html>
        <body>
            <h2>Consolidated Interview Analysis Report</h2>
            <p>Dear Team,</p>
            <p>The consolidated interview analysis report for <strong>{student_info.get('student_name')}</strong> 
            (Interview #{student_info.get('interview_id')}) is ready.</p>
            <p>This comprehensive report includes both technical skills assessment and behavioral analysis 
            generated using advanced AI technology.</p>
            <p>Best regards,<br>Interview Analysis System</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_content, 'html'))
        
        # Attach report
        if os.path.exists(report_path):
            with open(report_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename= {report_filename}')
                msg.attach(part)
        
        # Send email
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        if EMAIL_CONFIG['enable_ssl']:
            server.starttls()
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email sent successfully with report: {report_filename}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

# Main DAG Tasks
def find_interview_to_process(**context):
    """Find interview that needs processing - with completion tracking"""
    try:
        mysql_hook = MySqlHook(mysql_conn_id=DATABASE_CONN_ID)
        dag_run_id = context['dag_run'].run_id
        
        # Updated query to check completion tracking fields
        query = """
        SELECT i.id, i.student_id, u.first_name, u.last_name, u.email,
               i.questions_answered, i.total_questions, i.completion_percentage,
               i.completion_reason, i.has_audio_responses, i.audio_responses_count
        FROM interview_system_interview i
        LEFT JOIN user_management_customuser u ON i.student_id = u.id
        WHERE i.status = 'completed'
        AND i.analysis_completed = FALSE
        AND i.voice_interview_started = TRUE
        AND i.questions_answered > 0
        AND (i.processing_status IS NULL OR i.processing_status = 'pending')
        AND i.completed_at > NOW() - INTERVAL 72 HOUR
        ORDER BY i.completed_at ASC
        LIMIT 1
        """
        
        result = mysql_hook.get_first(query)
        
        if not result:
            logger.info("No interviews need processing (checking for interviews with voice data)")
            return 'no_interviews_to_process'
        
        interview_data = {
            'interview_id': result[0],
            'student_id': result[1],
            'student_name': f"{result[2]} {result[3]}",
            'student_email': result[4],
            'actual_user_id': result[1],
            'questions_answered': result[5],
            'total_questions': result[6],
            'completion_percentage': result[7],
            'completion_reason': result[8],
            'has_audio_responses': result[9],
            'audio_responses_count': result[10]
        }
        
        # Log completion details
        logger.info(f"Found interview {result[0]}: {interview_data['questions_answered']}/{interview_data['total_questions']} questions, {interview_data['completion_percentage']}% complete, reason: {interview_data['completion_reason']}")
        
        if not acquire_processing_lock(result[0], dag_run_id):
            logger.warning("Could not acquire processing lock")
            return 'no_interviews_to_process'
        
        update_processing_status(result[0], 'consolidated_processing_started')
        
        context['task_instance'].xcom_push(key='current_interview', value=interview_data)
        context['task_instance'].xcom_push(key='dag_run_id', value=dag_run_id)
        
        logger.info(f"Selected interview {result[0]} for processing: {interview_data['student_name']}")
        return 'generate_consolidated_report'
        
    except Exception as e:
        logger.error(f"Error finding interview: {e}")
        raise AirflowException(f"Failed to find interview: {e}")

def generate_consolidated_report(**context):
    """Generate consolidated report with LLM analysis"""
    interview = context['task_instance'].xcom_pull(key='current_interview')
    dag_run_id = context['task_instance'].xcom_pull(key='dag_run_id')
    
    if not interview:
        raise AirflowException("No interview data found")
    
    interview_id = interview['interview_id']
    
    try:
        logger.info(f"Generating consolidated report for interview {interview_id}")
        
        # Initialize report generator
        report_generator = ConsolidatedInterviewReportGenerator()
        
        # Read session data from HDFS
        session_data = report_generator.read_session_from_hdfs(interview_id)
        if not session_data:
            raise AirflowException("Could not read session data from HDFS")
        
        # Read combined analyzer result
        user_id = interview.get('actual_user_id', interview['student_id'])
        combined_result = report_generator.read_combined_analyzer_result(interview_id, user_id)
        
        # Generate behavioral analysis using LLM
        update_processing_status(interview_id, 'generating_behavioral_analysis')
        behavioral_analysis = report_generator.generate_behavioral_analysis(combined_result)
        
        # Generate technical analysis using LLM  
        update_processing_status(interview_id, 'generating_technical_analysis')
        technical_analysis = report_generator.generate_technical_analysis(session_data)
        
        # Generate consolidated PDF
        update_processing_status(interview_id, 'generating_pdf_report')
        file_path, filename = report_generator.generate_consolidated_pdf_report(
            interview_id, interview, behavioral_analysis, technical_analysis
        )
        
        if not file_path:
            raise AirflowException("Failed to generate PDF report")
        
        # Send email with report
        update_processing_status(interview_id, 'sending_email')
        email_sent = send_email_with_report(interview, file_path, filename)
        
        if email_sent:
            # Mark interview as fully completed with new tracking fields
            mysql_hook = MySqlHook(mysql_conn_id=DATABASE_CONN_ID)
            completion_query = """
            UPDATE interview_system_interview
            SET analysis_completed = TRUE, 
                processing_status = 'report_sent',
                processing_completed_at = NOW(),
                report_generated_at = NOW(),
                report_file_path = %s,
                report_sent_at = NOW(),
                report_sent_to = %s,
                last_processing_update = NOW()
            WHERE id = %s
            """
            recipients = ', '.join(EMAIL_CONFIG['report_recipients'])
            mysql_hook.run(completion_query, parameters=[file_path, recipients, interview_id])
            logger.info(f"Interview {interview_id} marked as FULLY COMPLETED with report tracking")
        
        return {
            'interview_id': interview_id,
            'report_generated': True,
            'report_path': file_path,
            'report_filename': filename,
            'email_sent': email_sent
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Consolidated report generation failed: {error_msg}")
        update_processing_status(interview_id, 'consolidated_report_failed')
        raise AirflowException(f"Report generation failed: {error_msg}")
        
    finally:
        if dag_run_id:
            release_processing_lock(dag_run_id)

def no_interviews_to_process(**context):
    """Handle case when no interviews need processing"""
    logger.info("No interviews need processing - system up to date")
    return "System up to date"

def cleanup_on_failure(**context):
    """Cleanup after processing failure"""
    try:
        dag_run_id = context['task_instance'].xcom_pull(key='dag_run_id')
        if dag_run_id:
            release_processing_lock(dag_run_id)
            logger.info("Released processing lock after failure")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

# Task Definitions
find_interview = BranchPythonOperator(
    task_id='find_interview_to_process',
    python_callable=find_interview_to_process,
    dag=dag
)

no_interviews = PythonOperator(
    task_id='no_interviews_to_process',
    python_callable=no_interviews_to_process,
    dag=dag
)

generate_report = PythonOperator(
    task_id='generate_consolidated_report',
    python_callable=generate_consolidated_report,
    dag=dag,
    execution_timeout=timedelta(minutes=90),
    retries=1
)

cleanup_failure = PythonOperator(
    task_id='cleanup_on_failure',
    python_callable=cleanup_on_failure,
    dag=dag,
    trigger_rule='one_failed'
)

# Task Dependencies
find_interview >> [no_interviews, generate_report]
generate_report >> cleanup_failure
