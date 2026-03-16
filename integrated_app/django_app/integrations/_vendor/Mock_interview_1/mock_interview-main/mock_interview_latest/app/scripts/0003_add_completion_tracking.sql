-- Migration Script: Interview Completion Tracking
-- Database: mock_interview_platform
-- Date: 2026-01-29
-- Description: Adds completion tracking fields to interview_system_interview and voice_interview_sessions tables

-- ========================================
-- INTERVIEW TABLE UPDATES
-- ========================================

-- Question/Response tracking
ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS total_questions INT DEFAULT 15 COMMENT 'Total questions in the interview';

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS questions_answered INT DEFAULT 0 COMMENT 'Number of questions answered by student';

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS voice_interview_started BOOLEAN DEFAULT FALSE COMMENT 'Did student start voice interview?';

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS voice_interview_completed BOOLEAN DEFAULT FALSE COMMENT 'Did student complete all questions?';

-- Completion details
ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS completion_reason VARCHAR(30) NULL 
COMMENT 'Why the interview ended: all_questions_answered, user_ended_early, timeout, error, admin_cancelled, expired, not_started';

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS completion_percentage FLOAT DEFAULT 0.0 COMMENT 'Percentage of interview completed (0-100)';

-- Duration tracking
ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS interview_duration_seconds INT NULL COMMENT 'Total interview duration in seconds';

-- Data availability flags (for DAG processing)
ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS has_audio_responses BOOLEAN DEFAULT FALSE COMMENT 'Are audio responses saved in HDFS?';

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS has_video_recording BOOLEAN DEFAULT FALSE COMMENT 'Is video recording available in Kafka?';

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS has_frame_data BOOLEAN DEFAULT FALSE COMMENT 'Are frames available for analysis?';

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS audio_responses_count INT DEFAULT 0 COMMENT 'Number of audio files saved';

-- Processing status (for DAG tracking)
ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS processing_status VARCHAR(20) DEFAULT 'pending' 
COMMENT 'Current processing status: pending, processing, analysis_complete, report_generated, report_sent, failed';

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS processing_started_at DATETIME NULL;

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS processing_completed_at DATETIME NULL;

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS processing_error TEXT NULL COMMENT 'Error message if processing failed';

-- Report tracking
ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS report_generated_at DATETIME NULL;

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS report_file_path TEXT NULL COMMENT 'Path to generated PDF report';

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS report_sent_at DATETIME NULL;

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS report_sent_to VARCHAR(254) NULL COMMENT 'Email address report was sent to';

-- ========================================
-- EMAIL TRACKING FIELDS (for optimized DAG)
-- ========================================

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS approval_email_sent BOOLEAN DEFAULT FALSE COMMENT 'Has approval email been sent?';

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS approval_email_sent_at DATETIME NULL;

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS rejection_email_sent BOOLEAN DEFAULT FALSE COMMENT 'Has rejection email been sent?';

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS rejection_email_sent_at DATETIME NULL;

ALTER TABLE interview_system_interview 
ADD COLUMN IF NOT EXISTS status_updated_at DATETIME NULL COMMENT 'Last status change timestamp';

-- ========================================
-- VOICE INTERVIEW SESSIONS TABLE UPDATES
-- ========================================

ALTER TABLE voice_interview_sessions 
ADD COLUMN IF NOT EXISTS session_status VARCHAR(20) DEFAULT 'not_started' 
COMMENT 'Current status: not_started, in_progress, completed, abandoned, error';

ALTER TABLE voice_interview_sessions 
ADD COLUMN IF NOT EXISTS total_questions_in_session INT DEFAULT 15;

ALTER TABLE voice_interview_sessions 
ADD COLUMN IF NOT EXISTS questions_with_audio_saved INT DEFAULT 0 
COMMENT 'Questions with audio successfully saved to HDFS';

ALTER TABLE voice_interview_sessions 
ADD COLUMN IF NOT EXISTS last_question_answered_at DATETIME NULL;

ALTER TABLE voice_interview_sessions 
ADD COLUMN IF NOT EXISTS voice_session_started_at DATETIME NULL;

ALTER TABLE voice_interview_sessions 
ADD COLUMN IF NOT EXISTS voice_session_ended_at DATETIME NULL;

ALTER TABLE voice_interview_sessions 
ADD COLUMN IF NOT EXISTS end_reason VARCHAR(50) NULL 
COMMENT 'Why the session ended: completed, user_ended, timeout, error';

ALTER TABLE voice_interview_sessions 
ADD COLUMN IF NOT EXISTS last_error TEXT NULL;

ALTER TABLE voice_interview_sessions 
ADD COLUMN IF NOT EXISTS error_count INT DEFAULT 0;

-- ========================================
-- ADD INDEXES FOR BETTER QUERY PERFORMANCE
-- ========================================

-- Index for DAG queries to find interviews ready for processing
CREATE INDEX IF NOT EXISTS idx_interview_processing_status 
ON interview_system_interview(processing_status, status);

-- Index for finding incomplete interviews
CREATE INDEX IF NOT EXISTS idx_interview_completion 
ON interview_system_interview(voice_interview_completed, questions_answered);

-- Index for report tracking queries
CREATE INDEX IF NOT EXISTS idx_interview_report_status 
ON interview_system_interview(report_sent_at, report_generated_at);

-- Index for voice session status
CREATE INDEX IF NOT EXISTS idx_voice_session_status 
ON voice_interview_sessions(session_status);

-- ========================================
-- UPDATE EXISTING DATA (Optional)
-- ========================================

-- Update existing completed interviews to have proper completion data
UPDATE interview_system_interview i
LEFT JOIN voice_interview_sessions vs ON i.id = vs.interview_id
SET 
    i.questions_answered = COALESCE(vs.current_question_number, 0),
    i.voice_interview_started = CASE WHEN vs.id IS NOT NULL THEN TRUE ELSE FALSE END,
    i.voice_interview_completed = CASE WHEN vs.current_question_number >= 15 THEN TRUE ELSE FALSE END,
    i.completion_percentage = CASE 
        WHEN vs.current_question_number IS NOT NULL THEN (vs.current_question_number / 15.0) * 100 
        ELSE 0 
    END,
    i.completion_reason = CASE 
        WHEN i.status = 'completed' AND vs.current_question_number >= 15 THEN 'all_questions_answered'
        WHEN i.status = 'completed' AND vs.current_question_number < 15 THEN 'user_ended_early'
        WHEN i.status = 'expired' THEN 'expired'
        WHEN i.status = 'cancelled' THEN 'admin_cancelled'
        ELSE NULL
    END
WHERE i.status IN ('completed', 'expired', 'cancelled');

-- Update audio response counts from actual response records
UPDATE interview_system_interview i
SET 
    i.audio_responses_count = (
        SELECT COUNT(*) 
        FROM interview_system_interviewresponse r 
        WHERE r.interview_id = i.id
    ),
    i.has_audio_responses = (
        SELECT COUNT(*) > 0 
        FROM interview_system_interviewresponse r 
        WHERE r.interview_id = i.id
    );

-- Update video/frame availability from frames table
UPDATE interview_system_interview i
LEFT JOIN interview_system_interviewframes f ON i.id = f.interview_id
SET 
    i.has_video_recording = CASE WHEN f.total_video_chunks > 0 THEN TRUE ELSE FALSE END,
    i.has_frame_data = CASE WHEN f.total_frames > 0 THEN TRUE ELSE FALSE END;

-- Update voice session status based on current state
UPDATE voice_interview_sessions
SET session_status = CASE
    WHEN current_question_number >= 15 THEN 'completed'
    WHEN current_question_number > 0 THEN 'in_progress'
    ELSE 'not_started'
END;

-- ========================================
-- VERIFICATION QUERIES
-- ========================================

-- Check column additions
SELECT 
    COLUMN_NAME, 
    DATA_TYPE, 
    IS_NULLABLE, 
    COLUMN_DEFAULT,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = 'mock_interview_platform' 
AND TABLE_NAME = 'interview_system_interview'
AND COLUMN_NAME IN (
    'total_questions', 'questions_answered', 'voice_interview_started', 
    'voice_interview_completed', 'completion_reason', 'completion_percentage',
    'processing_status', 'has_audio_responses', 'has_video_recording'
);

-- Check interview completion stats
SELECT 
    status,
    COUNT(*) as count,
    AVG(completion_percentage) as avg_completion,
    SUM(CASE WHEN voice_interview_completed THEN 1 ELSE 0 END) as fully_completed,
    SUM(CASE WHEN has_audio_responses THEN 1 ELSE 0 END) as with_audio
FROM interview_system_interview
GROUP BY status;

COMMIT;
