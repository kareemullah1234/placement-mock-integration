from datetime import datetime, timedelta
import json
import logging
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import pytz

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.providers.mysql.hooks.mysql import MySqlHook
from airflow.models import Variable
from airflow.exceptions import AirflowException
from airflow.utils.trigger_rule import TriggerRule

# IST Timezone utilities
def get_ist_now():
    """Get current time in IST"""
    return datetime.now(pytz.timezone('Asia/Kolkata'))

def format_ist_time(dt):
    """Format datetime for IST display"""
    if dt is None:
        return 'Not specified'
    if dt.tzinfo is None:
        # Assume UTC if no timezone info
        dt = pytz.UTC.localize(dt)
    ist_time = dt.astimezone(pytz.timezone('Asia/Kolkata'))
    return ist_time.strftime('%d %b %Y, %I:%M %p IST')

def convert_utc_to_ist(utc_dt):
    """Convert UTC datetime to IST"""
    if utc_dt is None:
        return None
    if utc_dt.tzinfo is None:
        utc_dt = pytz.UTC.localize(utc_dt)
    return utc_dt.astimezone(pytz.timezone('Asia/Kolkata'))

# Configuration
DATABASE_CONN_ID = "mysql_default"
EMAIL_ENABLED = Variable.get("EMAIL_ENABLED", default_var="true").lower() == "true"

# Email Configuration
EMAIL_CONFIG = {
    'smtp_server': Variable.get("EMAIL_SMTP_SERVER", default_var="smtp.gmail.com"),
    'smtp_port': int(Variable.get("EMAIL_SMTP_PORT", default_var="587")),
    'sender_email': Variable.get("EMAIL_SENDER", default_var="noreply@datamites.com"),
    'sender_password': Variable.get("EMAIL_PASSWORD", default_var="your-app-password"),
    'admin_emails': Variable.get("ADMIN_EMAILS", default_var="admin@datamites.com").split(','),
    'company_name': Variable.get("COMPANY_NAME", default_var="DataMites Mock Interview Platform"),
    'enable_ssl': Variable.get("EMAIL_SSL", default_var="true").lower() == "true"
}

# DAG Configuration
default_args = {
    'owner': 'interview-platform',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': EMAIL_ENABLED,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(hours=1),
    'email': EMAIL_CONFIG['admin_emails'],
    'execution_timeout': timedelta(minutes=30),
}

# DAG Definition
dag = DAG(
    'interview_status_email_notifications',
    default_args=default_args,
    description='Send IST timezone-aware email notifications for interview approvals/rejections',
    schedule_interval=timedelta(minutes=2),  # Check every 2 minutes for status changes
    catchup=False,
    max_active_runs=1,
    max_active_tasks=3,
    tags=['interview', 'email', 'notifications', 'approval', 'rejection', 'ist-timezone'],
)

# Email Service Class
class InterviewEmailService:
    def __init__(self):
        self.config = EMAIL_CONFIG

    def send_email(self, to_email, subject, html_content, retry_count=3):
        """Send email with retry mechanism"""
        if not EMAIL_ENABLED:
            logging.info(f"Email disabled, would send: {subject} to {to_email}")
            return True

        for attempt in range(retry_count):
            try:
                msg = MIMEMultipart('alternative')
                msg['From'] = self.config['sender_email']
                msg['To'] = to_email
                msg['Subject'] = subject

                msg.attach(MIMEText(html_content, 'html'))

                server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
                if self.config['enable_ssl']:
                    server.starttls()
                server.login(self.config['sender_email'], self.config['sender_password'])
                server.send_message(msg)
                server.quit()

                logging.info(f"✅ Email sent successfully to: {to_email} (attempt {attempt + 1})")
                return True

            except Exception as e:
                logging.warning(f"⚠️ Email attempt {attempt + 1} failed: {e}")
                if attempt < retry_count - 1:
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
                else:
                    logging.error(f"❌ Failed to send email to {to_email} after {retry_count} attempts: {e}")
                    raise e

        return False

    def generate_approval_email(self, student_info):
        """Generate IST timezone-aware approval email"""
        template = Template("""
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #ffffff;
                    line-height: 1.6;
                    color: #333333;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                }
                .content {
                    font-size: 16px;
                    line-height: 1.8;
                }
                .important {
                    font-weight: bold;
                    font-size: 18px;
                    margin: 20px 0;
                    color: #d73502;
                    background-color: #fff3cd;
                    padding: 15px;
                    border-left: 4px solid #d73502;
                }
                .details {
                    background-color: #f8f9fa;
                    padding: 20px;
                    margin: 20px 0;
                    border: 1px solid #dee2e6;
                }
                .time-info {
                    background-color: #e7f3ff;
                    padding: 15px;
                    margin: 15px 0;
                    border-left: 4px solid #0066cc;
                }
                .footer {
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #cccccc;
                    text-align: center;
                    color: #666666;
                    font-size: 14px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="content">
                    <p>Dear {{ student_name }},</p>

                    <p>Congratulations! Your request for an AI Mock Interview has been approved.</p>

                    <div class="details">
                        <p><strong>Interview Details:</strong></p>
                        <p>Candidate Name: {{ student_name }}</p>
                        <p>Attempt Number: #{{ attempt_number }}</p>
                        <p>Status: Approved</p>
                    </div>

                    <div class="time-info">
                        <p><strong>Scheduled Time: {{ scheduled_at_ist }}</strong></p>
                        <p><strong>Interview Window: {{ scheduled_at_ist }} to {{ expires_at_ist }}</strong></p>
                        <p><strong> Make Sure the interview is completed within 15 minutes.</strong></p>
                        <p><strong> All times are in Indian Standard Time (IST)</strong></p>
                    </div>

                    <div class="important">
                        <p>CRITICAL TIMING RULES:</p>
                        <p>• You can ONLY start at the EXACT scheduled time: {{ scheduled_at_ist }}</p>
                        <p>• NO early start allowed - button will be disabled until scheduled time</p>
                        <p>• Interview window closes at: {{ expires_at_ist }}</p>
                        <p>• NO grace period - please be ready at the scheduled time!</p>
                    </div>

                    <p><strong>Next Steps:</strong></p>
                    <p>1. <strong>Be ready 5 minutes before</strong> your scheduled time</p>
                    <p>2. Login to your Mock Interview Portal at {{ scheduled_at_ist }}</p>
                    <p>3. Navigate to your dashboard</p>
                    <p>4. The "Start Interview" button will become active at {{ scheduled_at_ist }}</p>
                    <p>5. Click "Start Interview" immediately when available</p>
                    <p>6. Ensure camera and microphone are working</p>

                    {% if admin_notes %}
                    <p><strong>Additional Notes:</strong> {{ admin_notes }}</p>
                    {% endif %}

                    <p><strong>Technical Requirements:</strong></p>
                    <p>• Test audio/video before scheduled time</p>
                    <p>• Use stable internet connection</p>
                    <p>• Chrome or Firefox browser recommended</p>
                    <p>• Quiet, well-lit space</p>
                    <p>• Professional attire</p>

                    <p>If you encounter technical issues, contact support: pat@datamites.com</p>

                    <p>Best of luck!</p>

                    <p>Best regards,<br>
                    DataMites Team</p>
                </div>

                <div class="footer">
                    <p>This is an automated message. Please do not reply.</p>
                    <p>Interview: {{ scheduled_at_ist }} | Window: 60 minutes | Timezone: IST</p>
                </div>
            </div>
        </body>
        </html>
        """)

        return template.render(**student_info)

    def generate_rejection_email(self, student_info):
        """Generate simple rejection email"""
        template = Template("""
        <html>
        <head>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #ffffff;
                    line-height: 1.6;
                    color: #333333;
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                }
                .content {
                    font-size: 16px;
                    line-height: 1.8;
                }
                .footer {
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #cccccc;
                    text-align: center;
                    color: #666666;
                    font-size: 14px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="content">
                    <p>Dear Candidate,</p>

                    <p>Thank you for your interest in our AI mock interview.</p>

                    <p>We regret to inform you that your request has been rejected as the email ID you used is not registered with DataMites.</p>

                    <p>To proceed with the mock interview, please ensure you are using the email ID associated with your DataMites registration. If you believe this is an error or need further assistance, feel free to contact our mock interview support team (pat@datamites.com).</p>

                    <p>We appreciate your understanding and look forward to helping you with your interview preparation.</p>

                    <p>Best regards,<br>
                    DataMites Team</p>
                </div>

                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """)

        return template.render(**student_info)

# Initialize email service
email_service = InterviewEmailService()

# Core Functions
def create_email_notification_tracking_table():
    """Create table to track email notifications"""
    try:
        mysql_hook = MySqlHook(mysql_conn_id=DATABASE_CONN_ID)

        create_table_query = """
        CREATE TABLE IF NOT EXISTS interview_email_notifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            interview_id INT NOT NULL,
            notification_type ENUM('approval', 'rejection') NOT NULL,
            email_sent BOOLEAN DEFAULT FALSE,
            email_sent_at TIMESTAMP NULL,
            email_status VARCHAR(50) DEFAULT 'pending',
            student_email VARCHAR(255),
            error_message TEXT,
            retry_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_notification (interview_id, notification_type),
            INDEX idx_email_status (email_status),
            INDEX idx_created_at (created_at)
        )
        """

        mysql_hook.run(create_table_query)
        logging.info("✅ Email notification tracking table ready")
        return True

    except Exception as e:
        logging.error(f"❌ Error creating email notification table: {e}")
        return False

def check_for_status_changes(**context):
    """Check for interview approvals and rejections with IST timezone handling - OPTIMIZED"""
    try:
        mysql_hook = MySqlHook(mysql_conn_id=DATABASE_CONN_ID)

        # Ensure tracking table exists
        if not create_email_notification_tracking_table():
            raise AirflowException("Failed to create email notification tracking table")

        # OPTIMIZED: Single query for approved interviews with better indexing
        approved_query = """
        SELECT
            i.id as interview_id,
            i.approved_at,
            i.scheduled_at,
            i.expires_at,
            i.admin_notes,
            i.attempt_number,
            u.first_name,
            u.last_name,
            u.email,
            i.student_id,
            i.approval_email_sent
        FROM interview_system_interview i
        JOIN user_management_customuser u ON i.student_id = u.id
        WHERE i.status = 'approved'
        AND i.approved_at IS NOT NULL
        AND i.scheduled_at IS NOT NULL
        AND i.approval_email_sent = FALSE
        AND i.approved_at > NOW() - INTERVAL 24 HOUR
        ORDER BY i.approved_at ASC
        LIMIT 10
        """

        # OPTIMIZED: Single query for rejected interviews using new tracking field
        rejected_query = """
        SELECT
            i.id as interview_id,
            i.admin_notes,
            i.attempt_number,
            i.requested_at,
            u.first_name,
            u.last_name,
            u.email,
            i.student_id,
            i.status_updated_at as decision_date
        FROM interview_system_interview i
        JOIN user_management_customuser u ON i.student_id = u.id
        WHERE i.status = 'cancelled'
        AND i.rejection_email_sent = FALSE
        AND i.status_updated_at > NOW() - INTERVAL 24 HOUR
        ORDER BY i.status_updated_at ASC
        LIMIT 10
        """

        approved_results = mysql_hook.get_records(approved_query)
        rejected_results = mysql_hook.get_records(rejected_query)

        notifications_to_process = []

        # Process approved interviews with IST timezone conversion
        for row in approved_results:
            interview_id = row[0]

            # Convert UTC times to IST for email display
            approved_at_ist = format_ist_time(row[1]) if row[1] else 'N/A'
            scheduled_at_ist = format_ist_time(row[2]) if row[2] else 'Not specified'
            expires_at_ist = format_ist_time(row[3]) if row[3] else 'N/A'

            notification_data = {
                'interview_id': interview_id,
                'type': 'approval',
                'student_name': f"{row[6]} {row[7]}",
                'student_email': row[8],
                'approved_at_ist': approved_at_ist,
                'scheduled_at_ist': scheduled_at_ist,
                'expires_at_ist': expires_at_ist,
                'admin_notes': row[4] or '',
                'attempt_number': row[5],
                'company_name': EMAIL_CONFIG['company_name']
            }
            notifications_to_process.append(notification_data)
            logging.info(f"📧 Queued approval email: Interview {interview_id} → {row[8]} (Scheduled: {scheduled_at_ist})")

        # Process rejected interviews
        for row in rejected_results:
            interview_id = row[0]

            # Convert times to IST for email
            requested_at_ist = format_ist_time(row[3]) if row[3] else 'N/A'
            decision_date_ist = format_ist_time(row[8]) if row[8] else 'N/A'

            notification_data = {
                'interview_id': interview_id,
                'type': 'rejection',
                'student_name': f"{row[4]} {row[5]}",
                'student_email': row[6],
                'admin_notes': row[1] or 'No specific reason provided',
                'attempt_number': row[2],
                'requested_at_ist': requested_at_ist,
                'decision_date_ist': decision_date_ist,
                'company_name': EMAIL_CONFIG['company_name']
            }
            notifications_to_process.append(notification_data)
            logging.info(f"📧 Queued rejection email: Interview {interview_id} → {row[6]}")

        if notifications_to_process:
            logging.info(f"📧 Total {len(notifications_to_process)} email notifications to process")
            context['task_instance'].xcom_push(key='notifications_to_process', value=notifications_to_process)
            return 'send_email_notifications'
        else:
            logging.info("✅ No new interview status changes requiring email notifications")
            return 'no_notifications_needed'

    except Exception as e:
        logging.error(f"❌ Error checking for status changes: {e}")
        raise AirflowException(f"Failed to check status changes: {e}")

def send_email_notifications(**context):
    """Send IST timezone-aware email notifications - OPTIMIZED"""
    notifications = context['task_instance'].xcom_pull(key='notifications_to_process')

    if not notifications:
        logging.info("No notifications to process")
        return {'total_notifications': 0, 'successful_emails': 0, 'failed_emails': 0}

    mysql_hook = MySqlHook(mysql_conn_id=DATABASE_CONN_ID)
    successful_emails = 0
    failed_emails = 0
    failed_notifications = []

    for notification in notifications:
        try:
            interview_id = notification['interview_id']
            notification_type = notification['type']
            student_email = notification['student_email']
            student_name = notification['student_name']

            logging.info(f"📧 Sending {notification_type} email for interview {interview_id} to {student_email}")

            # Generate appropriate email content
            if notification_type == 'approval':
                subject = f"🎯 Interview Scheduled - Start at {notification['scheduled_at_ist']} (Interview #{interview_id})"
                html_content = email_service.generate_approval_email(notification)
            else:
                subject = f"Interview Request Update (Interview #{interview_id})"
                html_content = email_service.generate_rejection_email(notification)

            # Send the email
            email_sent = email_service.send_email(student_email, subject, html_content)

            if email_sent:
                # OPTIMIZED: Update interview table directly instead of separate tracking table
                if notification_type == 'approval':
                    update_query = """
                    UPDATE interview_system_interview
                    SET approval_email_sent = TRUE,
                        approval_email_sent_at = NOW()
                    WHERE id = %s
                    """
                else:
                    update_query = """
                    UPDATE interview_system_interview
                    SET rejection_email_sent = TRUE,
                        rejection_email_sent_at = NOW()
                    WHERE id = %s
                    """
                mysql_hook.run(update_query, parameters=[interview_id])

                logging.info(f"✅ {notification_type.title()} email sent for interview {interview_id}")
                successful_emails += 1
            else:
                raise Exception("Email service returned failure")

        except Exception as e:
            error_msg = str(e)
            logging.error(f"❌ Failed to send {notification_type} email for interview {interview_id}: {error_msg}")
            failed_emails += 1
            failed_notifications.append({**notification, 'error': error_msg})

    # Log summary
    current_ist = get_ist_now().strftime('%Y-%m-%d %H:%M:%S IST')
    logging.info(f"📊 Email summary ({current_ist}): {successful_emails}/{len(notifications)} sent, {failed_emails} failed")

    result = {
        'total': len(notifications),
        'successful': successful_emails,
        'failed': failed_emails,
        'failed_notifications': failed_notifications
    }
    context['task_instance'].xcom_push(key='email_results', value=result)

    # Don't fail the task for partial failures - let admin alert handle it
    return result

def no_notifications_needed(**context):
    """Handle case when no notifications are needed"""
    current_ist = get_ist_now().strftime('%Y-%m-%d %H:%M:%S IST')
    logging.info(f"✅ No interview status email notifications needed at {current_ist}")
    return "No notifications needed"

def send_admin_failure_alert(**context):
    """Send IST timezone-aware admin alert for email failures"""
    try:
        email_results = context['task_instance'].xcom_pull(key='email_results')

        if not email_results or email_results.get('failed', 0) == 0:
            return "No admin alert needed"

        failed_notifications = [
            notif for notif in email_results.get('notifications', [])
        ]

        current_ist = get_ist_now().strftime('%Y-%m-%d %H:%M:%S IST')
        subject = f"🚨 Interview Email Notification Failures - {email_results['failed']} Failed ({current_ist})"

        html_content = f"""
        <html>
        <body>
            <h2 style="color: red;">Interview Email Notification Failures</h2>
            <p><strong>Failed Notifications:</strong> {email_results['failed']} out of {email_results['total']}</p>
            <p><strong>Timestamp (IST):</strong> {current_ist}</p>

            <h3>Failed Notifications:</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <th>Interview ID</th>
                    <th>Type</th>
                    <th>Student</th>
                    <th>Email</th>
                    <th>Scheduled Time (IST)</th>
                </tr>
        """

        for notif in failed_notifications:
            scheduled_time = notif.get('scheduled_at_ist', 'N/A') if notif['type'] == 'approval' else 'N/A'
            html_content += f"""
                <tr>
                    <td>{notif['interview_id']}</td>
                    <td>{notif['type'].title()}</td>
                    <td>{notif['student_name']}</td>
                    <td>{notif['student_email']}</td>
                    <td>{scheduled_time}</td>
                </tr>
            """

        html_content += f"""
            </table>

            <h3>Recommended Actions:</h3>
            <ul>
                <li>Check SMTP configuration and credentials</li>
                <li>Verify email addresses are valid</li>
                <li>Check Airflow logs for detailed error messages</li>
                <li>Review network connectivity to email server</li>
                <li>Manually notify affected students if needed</li>
            </ul>

            <p><strong>Note:</strong> All times are in Indian Standard Time (IST). The DAG will automatically retry failed notifications in the next run.</p>

            <p><strong>Current IST Time:</strong> {current_ist}</p>
        </body>
        </html>
        """

        # Send admin alert
        admin_email_sent = email_service.send_email(
            EMAIL_CONFIG['admin_emails'][0],
            subject,
            html_content
        )

        if admin_email_sent:
            logging.info(f"✅ Admin failure alert sent successfully at {current_ist}")
            return "Admin alert sent"
        else:
            logging.error(f"❌ Failed to send admin alert email at {current_ist}")
            return "Admin alert failed"

    except Exception as e:
        current_ist = get_ist_now().strftime('%Y-%m-%d %H:%M:%S IST')
        logging.error(f"❌ Error sending admin failure alert at {current_ist}: {e}")
        return f"Admin alert error: {e}"

def cleanup_old_notifications(**context):
    """Clean up old notification records"""
    try:
        mysql_hook = MySqlHook(mysql_conn_id=DATABASE_CONN_ID)

        # Delete notification records older than 7 days
        cleanup_query = """
        DELETE FROM interview_email_notifications
        WHERE created_at < NOW() - INTERVAL 7 DAY
        AND email_sent = TRUE
        """

        result = mysql_hook.run(cleanup_query)
        current_ist = get_ist_now().strftime('%Y-%m-%d %H:%M:%S IST')
        logging.info(f"🧹 Cleaned up old email notification records at {current_ist}")

        return "Cleanup completed"

    except Exception as e:
        current_ist = get_ist_now().strftime('%Y-%m-%d %H:%M:%S IST')
        logging.error(f"❌ Error during cleanup at {current_ist}: {e}")
        return f"Cleanup failed: {e}"

# Task Definitions
check_status_changes = BranchPythonOperator(
    task_id='check_for_status_changes',
    python_callable=check_for_status_changes,
    dag=dag,
    pool='default_pool'
)

no_notifications = PythonOperator(
    task_id='no_notifications_needed',
    python_callable=no_notifications_needed,
    dag=dag,
    pool='default_pool'
)

send_emails = PythonOperator(
    task_id='send_email_notifications',
    python_callable=send_email_notifications,
    dag=dag,
    pool='default_pool',
    retries=2,
    retry_delay=timedelta(minutes=3)
)

admin_failure_alert = PythonOperator(
    task_id='send_admin_failure_alert',
    python_callable=send_admin_failure_alert,
    dag=dag,
    pool='default_pool',
    trigger_rule=TriggerRule.ONE_FAILED,
)

cleanup_notifications = PythonOperator(
    task_id='cleanup_old_notifications',
    python_callable=cleanup_old_notifications,
    dag=dag,
    pool='default_pool',
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
)

# Task Dependencies
check_status_changes >> [no_notifications, send_emails]
send_emails >> [admin_failure_alert, cleanup_notifications]

# Documentation
"""
Interview Status Email Notification DAG - Updated with IST Timezone Support

🕐 NEW IST TIMEZONE FEATURES:
- All email times displayed in Indian Standard Time (IST)
- Proper UTC to IST conversion for database times
- IST-aware logging and admin alerts
- Timezone information included in emails

📧 EMAIL FORMATS WITH IST:
- Approval: Shows exact scheduled time in IST with strict timing rules
- Rejection: Simple format with IST timestamps
- Admin alerts: IST timestamps for failure notifications

🔧 SETUP STEPS:

1. Save this file as: /path/to/airflow/dags/interview_status_email_notifications.py

2. Configure Airflow Variables:
   airflow variables set EMAIL_ENABLED "true"
   airflow variables set EMAIL_SMTP_SERVER "smtp.gmail.com"
   airflow variables set EMAIL_SMTP_PORT "587"
   airflow variables set EMAIL_SENDER "noreply@datamites.com"
   airflow variables set EMAIL_PASSWORD "your-app-password"
   airflow variables set ADMIN_EMAILS "admin@datamites.com"
   airflow variables set COMPANY_NAME "DataMites Mock Interview Platform"
   airflow variables set EMAIL_SSL "true"

3. Install required Python packages in Airflow environment:
   pip install pytz jinja2

4. Ensure MySQL connection 'mysql_default' is configured in Airflow

5. Test the DAG:
   airflow dags test interview_status_email_notifications

📊 WHAT'S CHANGED FOR IST SUPPORT:

✅ Added IST timezone utilities:
   - get_ist_now(): Get current IST time
   - format_ist_time(): Format UTC times as IST for display
   - convert_utc_to_ist(): Convert UTC datetime to IST

✅ Updated approval email template:
   - Shows scheduled time in IST format
   - Clear timezone information
   - Strict timing rules explanation
   - No grace period warnings

✅ Enhanced SQL queries:
   - Proper timezone handling for database queries
   - IST time conversion for email data

✅ Improved logging:
   - All log timestamps now show IST
   - Better timezone awareness in admin alerts

🎯 WORKFLOW WITH IST:
1. Admin schedules interview for "4:30 PM IST" in Django admin
2. Django stores as UTC in database (11:00 AM UTC)
3. DAG detects approval and converts times to IST for email
4. Student receives email: "Scheduled for 29 Jul 2025, 04:30 PM IST"
5. All logging and admin alerts show IST times

📋 MONITORING:
- Check logs: grep "IST" /path/to/airflow/logs/interview_status_email_notifications/
- Database: SELECT * FROM interview_email_notifications;
- Test email templates with sample data

🚨 IMPORTANT NOTES:
- Database times remain in UTC (don't change this)
- Only email display and logging use IST
- Matches the Django views timezone handling
- Admin alerts include IST timestamps
- All student-facing times are in IST

🔄 COMPATIBILITY:
- Works with existing Django timezone changes
- Matches frontend button behavior
- Consistent with backend time validation
- No database schema changes needed

This DAG now properly handles IST timezone display while maintaining UTC storage,
ensuring consistency with your Django application's timezone handling.
"""