import json
from typing import Dict, List, Any
from pathlib import Path

DB_PATH = Path(__file__).parent / "2024_cindy_industry_grouped_combined.json"

class MADatabase:
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.load_data()

    def load_data(self):
        with open(DB_PATH, 'r') as file:
            self.data = json.load(file)

    def get_awards(self, industry: str, subindustry: str = None) -> List[Dict[str, Any]]:
        awards = []
        if industry in self.data:
            if subindustry and subindustry in self.data[industry]:
                for award_id, award_data in self.data[industry][subindustry].items():
                    awards.append({
                        "award_id": award_id,
                        "award_name": award_data["Award Name"],
                        "coverage_clauses": award_data["Coverage Clauses"]
                    })
            else:
                for subind in self.data[industry].values():
                    for award_id, award_data in subind.items():
                        awards.append({
                            "award_id": award_id,
                            "award_name": award_data["Award Name"],
                            "coverage_clauses": award_data["Coverage Clauses"]
                        })
        return awards

    def get_jobs(self, industry: str, subindustry: str = None) -> List[Dict[str, str]]:
        jobs = []
        if industry in self.data:
            if subindustry and subindustry in self.data[industry]:
                for award_data in self.data[industry][subindustry].values():
                    jobs.extend(award_data["Jobs"])
            else:
                for subind in self.data[industry].values():
                    for award_data in subind.values():
                        jobs.extend(award_data["Jobs"])
        return jobs

    def get_qualifications(self, industry: str, subindustry: str = None) -> List[str]:
        qualifications = set()
        if industry in self.data:
            if subindustry and subindustry in self.data[industry]:
                for award_data in self.data[industry][subindustry].values():
                    qualifications.update(award_data["Qualifications"])
            else:
                for subind in self.data[industry].values():
                    for award_data in subind.values():
                        qualifications.update(award_data["Qualifications"])
        return list(qualifications)
    
ma_db = MADatabase()