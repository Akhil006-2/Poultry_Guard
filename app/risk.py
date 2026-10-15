"""Conservative rules for triage; never a veterinary diagnosis."""

def assess_event(signs, sick_count=0, deaths=0, feed_change="unknown", water_change="unknown"):
    normalized = {str(s).strip().lower() for s in (signs or [])}
    severe = {"breathing difficulty", "bloody droppings", "neurological signs", "sudden collapse", "blue comb"}
    common = {"lethargy", "diarrhea", "coughing/sneezing", "reduced movement", "reduced appetite", "abnormal droppings"}
    if deaths >= 2 or normalized.intersection(severe):
        level = "urgent"
        advice = "Contact a poultry veterinarian or local animal-health authority promptly. Limit unnecessary movement between flocks and follow local biosecurity guidance."
    elif deaths == 1 or sick_count >= 2 or normalized.intersection(common) or feed_change == "decreased" or water_change == "decreased":
        level = "watch"
        advice = "Recheck the flock and water/feed records, isolate visibly sick birds where appropriate, and seek veterinary advice if signs persist or worsen."
    else:
        level = "routine"
        advice = "Continue routine observation and record daily mortality, feed, water, and behavior."
    return {"risk_level": level, "advice": advice, "is_diagnosis": False}
