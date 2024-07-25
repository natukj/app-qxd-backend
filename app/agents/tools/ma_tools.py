classify_tools = [
    {
        "type": "function",
        "function": {
            "name": "classify_employee",
            "description": "Classify an employee under the correct Modern Award and level.",
            "parameters": {
                "type": "object",
                "properties": {
                    "award_id": {
                        "type": "string",
                        "description": "The ID of the Modern Award that applies to the employee under eg. 'MA000001'"
                    },
                    "award_reasoning": {
                        "type": "string",
                        "description": "Your succinct reasoning for classifying the employee under the specified Modern Award."
                    },
                    "award_clauses": {
                        "type": "string",
                        "description": "Array of strings, containing all clauses that you used to make your award decision. For example: [\"1.1\", \"34.2\", \"A.1.14\"]"
                    },
                    "level": {
                        "type": "string",
                        "description": "Classification level of the employee under the specified Modern Award, eg. Level 1 or Level 2"
                    },
                    "level_reasoning": {
                        "type": "string",
                        "description": "Your succinct reasoning for classifying the employee at a specific level."
                    },
                    "level_clauses": {
                        "type": "string",
                        "description": "Array of strings, containing all clauses that you used to make your level decision. For example: [\"1.1\", \"34.2\", \"A.1.14\"]"
                    },
                    "try_again": {
                        "type": "boolean",
                        "description": "If the award(s) do not cover the employee, set this to True to see additional awards."
                    }
                },
                "required": ["award_id", "award_reasoning", "award_clauses", "level", "level_reasoning", "level_clauses"]
            }
        }
    }
]