from .models import Skill

def attach_skills(skill_list, obj):

    for skill in skill_list:

        skill = skill.strip().lower()

        skill_obj, created = Skill.objects.get_or_create(name=skill)

        obj.skills.add(skill_obj)