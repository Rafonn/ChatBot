from thefuzz import process


class FuzzyMatcher:
    @staticmethod
    def match(machine_name_db: str, machines_names: list, threshold: int = 80) -> str:
        best_match, score = process.extractOne(machine_name_db, machines_names)
        return best_match if score >= threshold else None
