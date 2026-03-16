from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db import models
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta
import json
from .models import CustomUser, StudentProfile
from interview_system.models import Interview

def debug_headers(request):
    """Debug function to check request headers for CSRF troubleshooting"""
    return JsonResponse({
        'HTTP_HOST': request.META.get('HTTP_HOST'),
        'HTTP_ORIGIN': request.META.get('HTTP_ORIGIN'),
        'HTTP_X_FORWARDED_PROTO': request.META.get('HTTP_X_FORWARDED_PROTO'),
        'HTTP_X_FORWARDED_HOST': request.META.get('HTTP_X_FORWARDED_HOST'),
        'HTTP_REFERER': request.META.get('HTTP_REFERER'),
        'is_secure': request.is_secure(),
        'scheme': request.scheme,
        'path': request.path,
        'get_host': request.get_host(),
        'build_absolute_uri': request.build_absolute_uri(),
        'all_headers': {k: v for k, v in request.META.items() if k.startswith('HTTP_')}
    })

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Authenticate using email as username
        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Your account has been deactivated. Please contact admin.')
        else:
            messages.error(request, 'Invalid email or password')

    return render(request, 'user_management/login.html')

def register_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number', '')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        # Validation
        if password != password_confirm:
            messages.error(request, "Passwords don't match")
            return render(request, 'user_management/register.html')

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return render(request, 'user_management/register.html')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists')
            return render(request, 'user_management/register.html')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'user_management/register.html')

        try:
            with transaction.atomic():
                # Create user
                user = CustomUser.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=password,
                    phone_number=phone_number,
                    is_student=True,
                    is_admin=False
                )

                # Create student profile
                StudentProfile.objects.create(
                    user=user,
                    student_id=f"STU{user.id:06d}"
                )

                messages.success(request, 'Registration successful! Please login with your credentials.')
                return redirect('login')

        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')

    return render(request, 'user_management/register.html')

@login_required
def dashboard_view(request):
    # Check if user is admin or staff
    if request.user.is_admin or request.user.is_staff or request.user.is_superuser:
        return render(request, 'user_management/admin_dashboard.html')
    else:
        # Expire any approved interviews that have timed out
        expired_interviews = Interview.objects.filter(
            student=request.user,
            status='approved',
            expires_at__lt=timezone.now()
        )
        expired_interviews.update(
            status='expired',
            admin_notes='Interview expired - not started within 10 minutes of approval'
        )

        # Get user's interview statistics
        user_interviews = Interview.objects.filter(student=request.user)
        completed_interviews = user_interviews.filter(status='completed')

        context = {
            'total_interviews': user_interviews.count(),
            'completed_interviews': completed_interviews.count(),
            'pending_interviews': user_interviews.filter(status__in=['requested', 'approved', 'in_progress']).count(),
            'average_score': completed_interviews.filter(analysis_completed=True).aggregate(
                avg_score=models.Avg('overall_score')
            )['avg_score'] or 0,
            'recent_interviews': user_interviews.order_by('-created_at')[:10]
        }
        return render(request, 'user_management/student_dashboard.html', context)

def logout_view(request):
    user_name = request.user.first_name if request.user.is_authenticated else 'User'
    logout(request)
    messages.info(request, f'Goodbye {user_name}! You have been logged out.')
    return redirect('login')


@login_required
@require_http_methods(["POST"])
def update_profile(request):
    """Update student profile including availability information"""
    try:
        data = json.loads(request.body)
        user = request.user

        # Update user fields
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.email = data.get('email', user.email)
        user.phone_number = data.get('phone_number', user.phone_number)
        user.save()

        # Update or create student profile
        profile, created = StudentProfile.objects.get_or_create(
            user=user,
            defaults={'student_id': f"STU{user.id:06d}"}
        )

        # Update basic profile fields
        profile.college = data.get('college', profile.college)
        profile.course = data.get('course', profile.course)
        profile.year_of_study = data.get('year_of_study') or None
        profile.skills = data.get('skills', profile.skills)
        
        # Update availability fields
        profile.batch_id = data.get('batch_id', profile.batch_id)
        profile.interview_preference = data.get('interview_preference', profile.interview_preference)
        
        # Process availability slots
        availability_slots = data.get('availability_slots', [])
        if availability_slots:
            # Validate that we have exactly 3 slots
            if len(availability_slots) == 3:
                profile.availability_slots = availability_slots
                profile.availability_updated_at = timezone.now()
        
        profile.save()

        return JsonResponse({
            'success': True,
            'message': 'Profile updated successfully',
            'has_complete_availability': profile.has_complete_availability()
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)



@login_required
def get_all_interviews(request):
    """Get all interviews for the current student"""
    try:
        # Expire any approved interviews that have timed out
        expired_interviews = Interview.objects.filter(
            student=request.user,
            status='approved',
            expires_at__lt=timezone.now()
        )
        expired_interviews.update(
            status='expired',
            admin_notes='Interview expired - not started within 10 minutes of approval'
        )

        interviews = Interview.objects.filter(student=request.user).order_by('-created_at')
        interviews_data = []

        for interview in interviews:
            data = {
                'id': str(interview.id),
                'attempt_number': interview.attempt_number,
                'status': interview.status,
                'created_at': interview.created_at.isoformat(),
                'requested_at': interview.requested_at.isoformat() if interview.requested_at else None,
                'approved_at': interview.approved_at.isoformat() if interview.approved_at else None,
                'scheduled_at': interview.scheduled_at.isoformat() if interview.scheduled_at else None,
                'started_at': interview.started_at.isoformat() if interview.started_at else None,
                'completed_at': interview.completed_at.isoformat() if interview.completed_at else None,
                'overall_score': interview.overall_score,
                'cheating_detected': interview.cheating_detected,
                'analysis_completed': interview.analysis_completed,
                'admin_notes': interview.admin_notes,
                'time_remaining': interview.time_remaining() if interview.status == 'approved' else 0,
                'is_expired': interview.is_expired()
            }
            interviews_data.append(data)

        return JsonResponse(interviews_data, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
# Add this new function to your user_management/views.py

@login_required
def check_availability_status(request):
    """Check if user has complete availability information"""
    try:
        profile = getattr(request.user, 'student_profile', None)
        if not profile:
            return JsonResponse({
                'has_complete_availability': False,
                'message': 'Profile not found'
            })

        return JsonResponse({
            'has_complete_availability': profile.has_complete_availability(),
            'availability_summary': profile.get_availability_summary() if profile.has_complete_availability() else None,
            'batch_id': profile.batch_id or '',
            'interview_preference': profile.interview_preference or '',
            'availability_slots': profile.availability_slots or []
        })

    except Exception as e:
        return JsonResponse({
            'has_complete_availability': False,
            'error': str(e)
        }, status=500)

# Replace the get_students_list function in user_management/views.py

@staff_member_required
def get_students_list(request):
    """Get list of students for admin dashboard with availability info"""
    try:
        students = CustomUser.objects.filter(is_student=True).select_related('student_profile')
        students_data = []

        for student in students:
            profile = getattr(student, 'student_profile', None)

            students_data.append({
                'id': student.id,
                'full_name': student.get_full_name(),
                'email': student.email,
                'phone_number': student.phone_number or 'N/A',
                'student_id': profile.student_id if profile else 'N/A',
                'interview_count': student.interviews.count(),
                'is_active': student.is_active,
                'date_joined': student.date_joined.strftime('%Y-%m-%d'),
                'last_login': student.last_login.strftime('%Y-%m-%d %H:%M') if student.last_login else 'Never',
                
                # FIXED: Add detailed availability information
                'batch_id': profile.batch_id if profile else 'Not Set',
                'student_batch_id': profile.batch_id if profile else 'Not Set',  # Add alternate field name
                'interview_preference': profile.get_interview_preference_display() if profile and profile.interview_preference else 'Not Set',
                'student_preference': profile.get_interview_preference_display() if profile and profile.interview_preference else 'Not Set',  # Add alternate field name
                'has_complete_availability': profile.has_complete_availability() if profile else False,
                'availability_summary': profile.get_availability_summary() if profile else 'Not Available',
                'student_availability_summary': profile.get_availability_summary() if profile else 'Not Available',  # Add alternate field name
                'availability_updated_at': profile.availability_updated_at.strftime('%Y-%m-%d %H:%M') if profile and profile.availability_updated_at else 'Never',
                
                # CRITICAL: Add the detailed availability slots that the frontend expects
                'availability_slots': profile.availability_slots if profile and profile.availability_slots else [],
                'student_availability_slots': profile.availability_slots if profile and profile.availability_slots else [],  # Add alternate field name
                
                # Additional student info that might be useful
                'student_name': student.get_full_name(),  # Add alternate field name
                'student_email': student.email,  # Add alternate field name
            })

        return JsonResponse(students_data, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def get_interviews_list(request):
    """Get list of interviews for admin dashboard with availability info"""
    try:
        # First expire any approved interviews that have timed out
        expired_interviews = Interview.objects.filter(
            status='approved',
            expires_at__lt=timezone.now()
        )
        expired_interviews.update(
            status='expired',
            admin_notes='Interview expired - not started within 10 minutes of approval'
        )

        interviews = Interview.objects.select_related('student').order_by('-created_at')[:100]
        interviews_data = []

        for interview in interviews:
            student_profile = getattr(interview.student, 'student_profile', None)

            # Calculate time remaining for approved interviews
            time_remaining = 0
            if interview.status == 'approved' and interview.expires_at:
                remaining_seconds = (interview.expires_at - timezone.now()).total_seconds()
                time_remaining = max(0, int(remaining_seconds / 60))

            interviews_data.append({
                # Basic interview info
                'id': str(interview.id),
                'student_name': interview.student.get_full_name(),
                'student_email': interview.student.email,
                'student_id': student_profile.student_id if student_profile else 'N/A',
                'created_at': interview.created_at.isoformat(),
                'requested_at': interview.requested_at.isoformat() if interview.requested_at else None,
                'approved_at': interview.approved_at.isoformat() if interview.approved_at else None,
                'scheduled_at': interview.scheduled_at.isoformat() if interview.scheduled_at else None,
                'expires_at': interview.expires_at.isoformat() if interview.expires_at else None,
                'status': interview.status,
                'overall_score': interview.overall_score,
                'cheating_detected': interview.cheating_detected,
                'cheating_confidence': interview.cheating_confidence or 0,
                'analysis_completed': interview.analysis_completed,
                'attempt_number': interview.attempt_number,
                'admin_notes': interview.admin_notes,
                'time_remaining': time_remaining,
                
                # FIXED: Add complete availability information
                'student_batch_id': student_profile.batch_id if student_profile else 'Not Set',
                'student_preference': student_profile.get_interview_preference_display() if student_profile and student_profile.interview_preference else 'Not Set',
                'has_complete_availability': student_profile.has_complete_availability() if student_profile else False,
                'availability_summary': student_profile.get_availability_summary() if student_profile else 'Not Available',
                'student_availability_summary': student_profile.get_availability_summary() if student_profile else 'Not Available',
                'availability_updated_at': student_profile.availability_updated_at.strftime('%Y-%m-%d %H:%M') if student_profile and student_profile.availability_updated_at else 'Never',
                
                # CRITICAL: Add detailed availability slots
                'student_availability_slots': student_profile.availability_slots if student_profile and student_profile.availability_slots else [],
                'availability_slots': student_profile.availability_slots if student_profile and student_profile.availability_slots else [],
                
                # Additional fields for consistency
                'batch_id': student_profile.batch_id if student_profile else 'Not Set',
                'interview_preference': student_profile.interview_preference if student_profile else None,
            })

        return JsonResponse(interviews_data, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@staff_member_required
@require_http_methods(["POST"])
def approve_interview(request, interview_id):
    """Approve an interview request and schedule it"""
    try:
        data = json.loads(request.body)
        interview = Interview.objects.get(id=interview_id, status='requested')

        interview.status = 'approved'
        interview.approved_at = timezone.now()
        interview.approved_by = request.user

        # Set 10-minute expiration
        interview.expires_at = timezone.now() + timedelta(minutes=10)

        # Handle scheduled_at with timezone awareness
        scheduled_at_str = data.get('scheduled_at')
        if scheduled_at_str:
            scheduled_dt = parse_datetime(scheduled_at_str)
            if scheduled_dt:
                if timezone.is_naive(scheduled_dt):
                    scheduled_dt = timezone.make_aware(scheduled_dt)
                interview.scheduled_at = scheduled_dt
            else:
                interview.scheduled_at = timezone.now()
        else:
            interview.scheduled_at = timezone.now()

        interview.admin_notes = data.get('admin_notes', '')
        interview.save()

        return JsonResponse({
            'success': True,
            'message': 'Interview approved and scheduled successfully. Student has 10 minutes to start.',
            'expires_at': interview.expires_at.isoformat()
        })

    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview request not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
@require_http_methods(["POST"])
def reject_interview(request, interview_id):
    """Reject an interview request"""
    try:
        data = json.loads(request.body)
        interview = Interview.objects.get(id=interview_id, status='requested')

        interview.status = 'cancelled'
        interview.admin_notes = data.get('admin_notes', 'Request rejected by admin')
        interview.save()

        return JsonResponse({
            'success': True,
            'message': 'Interview request rejected'
        })

    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview request not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
@require_http_methods(["POST"])
def toggle_student_status(request, student_id):
    """Toggle student active status"""
    try:
        student = CustomUser.objects.get(id=student_id, is_student=True)
        student.is_active = not student.is_active
        student.save()

        return JsonResponse({
            'success': True,
            'message': f'Student status updated to {"Active" if student.is_active else "Inactive"}',
            'is_active': student.is_active
        })

    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
@require_http_methods(["POST"])
def delete_student(request, student_id):
    """Delete a student (soft delete by deactivating)"""
    try:
        student = CustomUser.objects.get(id=student_id, is_student=True)
        student.is_active = False
        student.save()

        return JsonResponse({
            'success': True,
            'message': 'Student deactivated successfully'
        })

    except CustomUser.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
@require_http_methods(["POST"])
def delete_interview(request, interview_id):
    """Delete an interview"""
    try:
        interview = Interview.objects.get(id=interview_id)
        interview.delete()

        return JsonResponse({
            'success': True,
            'message': 'Interview deleted successfully'
        })

    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# API endpoints for AJAX calls
@require_http_methods(["POST"])
def api_login(request):
    try:
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')

        user = authenticate(request, username=email, password=password)
        if user is not None and user.is_active:
            login(request, user)
            return JsonResponse({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.get_full_name(),
                    'is_student': user.is_student,
                    'is_admin': user.is_admin or user.is_staff
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid credentials or account deactivated'
            }, status=400)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
def api_register(request):
    try:
        data = json.loads(request.body)

        # Validation
        if CustomUser.objects.filter(email=data.get('email')).exists():
            return JsonResponse({
                'success': False,
                'error': 'Email already exists'
            }, status=400)

        if CustomUser.objects.filter(username=data.get('username')).exists():
            return JsonResponse({
                'success': False,
                'error': 'Username already exists'
            }, status=400)

        with transaction.atomic():
            user = CustomUser.objects.create_user(
                username=data.get('username'),
                email=data.get('email'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                password=data.get('password'),
                phone_number=data.get('phone_number', ''),
                is_student=True
            )

            StudentProfile.objects.create(
                user=user,
                student_id=f"STU{user.id:06d}"
            )

        return JsonResponse({
            'success': True,
            'message': 'Registration successful',
            'user_id': user.id
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
