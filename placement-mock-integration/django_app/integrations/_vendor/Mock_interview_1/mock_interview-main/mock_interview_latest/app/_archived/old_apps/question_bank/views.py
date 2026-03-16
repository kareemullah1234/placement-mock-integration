from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
import os
import logging
from .services import QuestionService

logger = logging.getLogger(__name__)

@csrf_exempt
@login_required
def get_questions_list(request):
    """Get list of available questions"""
    try:
        question_service = QuestionService()
        questions = question_service.get_random_questions()
        
        logger.info(f"Serving {len(questions)} questions to user {request.user.id}")
        
        return JsonResponse({
            'questions': questions,
            'count': len(questions),
            'message': 'Questions loaded successfully'
        })
        
    except Exception as e:
        logger.error(f"Error in get_questions_list: {e}")
        return JsonResponse({
            'error': str(e),
            'questions': []
        }, status=500)

@csrf_exempt
@login_required
def get_question_audio(request, folder, filename):
    """Serve question audio file"""
    try:
        question_service = QuestionService()
        question_path = f"{folder}/{filename}"
        
        logger.info(f"Serving audio: {question_path}")
        
        audio_data = question_service.get_question_audio(question_path)
        
        if audio_data:
            response = HttpResponse(audio_data, content_type='audio/wav')
            response['Content-Length'] = len(audio_data)
            response['Accept-Ranges'] = 'bytes'
            response['Cache-Control'] = 'no-cache'
            return response
        else:
            logger.warning(f"Audio file not found: {question_path}")
            return JsonResponse({
                'error': 'Audio file not found',
                'path': question_path
            }, status=404)
            
    except Exception as e:
        logger.error(f"Error serving audio {folder}/{filename}: {e}")
        return JsonResponse({
            'error': str(e),
            'path': f"{folder}/{filename}"
        }, status=500)
