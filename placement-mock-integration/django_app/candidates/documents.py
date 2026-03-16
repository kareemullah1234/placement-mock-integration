from django_elasticsearch_dsl import Document, Index
from .models import CandidateProfile

candidate_index = Index('candidates')

@candidate_index.doc_type
class CandidateDocument(Document):
    class Django:
        model = CandidateProfile
        fields = [
            'extracted_skills',
        ]