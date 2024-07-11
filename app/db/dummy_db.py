import json
from typing import Dict, List, Any
from pathlib import Path

PROJECT_MAPPING = {
    'modern-awards': {
        'name': 'Modern Awards',
        'description': 'Explore the comprehensive guide to Modern Awards in Australian employment law.',
    },
    'modern-award-classification': {
        'name': 'Modern Award Classification',
        'description': 'Classification system within Modern Awards.',
    },
    'fair-work-act': {
        'name': 'Fair Work Act',
        'description': 'Dive into the Fair Work Act and its impact on Australian employment regulations.',
    },
    'income-tax-assessment-act': {
        'name': 'Income Tax Assessment Act',
        'description': 'Navigate the complexities of the Income Tax Assessment Act and its provisions.',
    },
}

DB_PATH = Path(__file__).parent / "dummy_db.json"

def read_db() -> Dict[str, Any]:
    with open(DB_PATH, "r") as f:
        return json.load(f)

def write_db(data: Dict[str, Any]):
    with open(DB_PATH, "w") as f:
        json.dump(data, f, indent=4)

def get_user(username: str) -> Dict[str, Any]:
    db = read_db()
    return db["users"].get(username)

def add_project(username: str, project_id: str, project_data: Dict[str, Any]) -> bool:
    db = read_db()
    if username not in db["users"]:
        return False
    
    if project_id in db["projects"]:
        return True  
    
    db["projects"][project_id] = project_data
    db["users"][username]["projects"].append(project_id)
    
    write_db(db)
    return True

def get_user_projects(username: str) -> List[Dict[str, Any]]:
    db = read_db()
    user = db["users"].get(username)
    if not user:
        return []
    
    projects = []
    for project_id in user["projects"]:
        project_info = PROJECT_MAPPING.get(project_id, {})
        projects.append({
            "id": project_id,
            "name": project_info.get("name", project_id),
            "description": project_info.get("description", "")
        })
    return projects

def get_user_project(username: str, project_id: str) -> Dict[str, Any]:
    db = read_db()
    user = db["users"].get(username)
    if not user or project_id not in user["projects"]:
        return None
    
    project_info = PROJECT_MAPPING.get(project_id, {})
    return {
        "id": project_id,
        "name": project_info.get("name", project_id),
        "description": project_info.get("description", "")
    }


def verify_password(username: str, password: str) -> bool:
    user = get_user(username)
    if not user:
        return False
    return user["hashed_password"] == "fakehashedsecret" and password == "secret"
