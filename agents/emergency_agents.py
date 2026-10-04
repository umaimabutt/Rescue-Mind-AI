from difflib import SequenceMatcher
from math import radians, sin, cos, sqrt, atan2


# =========================================
# TEXT SIMILARITY
# =========================================

def text_similarity(text_a, text_b):

    text_a = (text_a or "").lower().strip()
    text_b = (text_b or "").lower().strip()

    if not text_a or not text_b:
        return 0.0

    sequence_score = SequenceMatcher(
        None,
        text_a,
        text_b
    ).ratio()

    words_a = set(text_a.split())
    words_b = set(text_b.split())

    if words_a or words_b:

        intersection = len(
            words_a.intersection(words_b)
        )

        union = len(
            words_a.union(words_b)
        )

        jaccard_score = (
            intersection / union
            if union
            else 0
        )

    else:

        jaccard_score = 0


    return round(
        (sequence_score * 0.6)
        + (jaccard_score * 0.4),
        3
    )


# =========================================
# DISTANCE
# =========================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2
):

    try:

        lat1 = float(lat1)
        lon1 = float(lon1)

        lat2 = float(lat2)
        lon2 = float(lon2)

    except Exception:

        return None


    radius = 6371.0

    dlat = radians(
        lat2 - lat1
    )

    dlon = radians(
        lon2 - lon1
    )

    a = (
        sin(dlat / 2) ** 2
        +
        cos(radians(lat1))
        *
        cos(radians(lat2))
        *
        sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return radius * c


# =========================================
# DUPLICATE DETECTION
# =========================================

def duplicate_candidates(
    current_report,
    existing_reports,
    threshold=0.55
):

    results = []

    current_text = (
        current_report.get("description")
        or ""
    )

    current_lat = (
        current_report.get("latitude")
    )

    current_lon = (
        current_report.get("longitude")
    )

    for report in existing_reports:

        similarity = text_similarity(
            current_text,
            report.get("description") or ""
        )

        distance = None

        if (
            current_lat is not None
            and current_lon is not None
            and report.get("latitude") is not None
            and report.get("longitude") is not None
        ):

            distance = haversine_km(
                current_lat,
                current_lon,
                report.get("latitude"),
                report.get("longitude")
            )


        location_bonus = 0

        if distance is not None:

            if distance <= 1:
                location_bonus = 0.25

            elif distance <= 3:
                location_bonus = 0.15

            elif distance <= 5:
                location_bonus = 0.05


        final_score = min(
            1.0,
            similarity + location_bonus
        )


        if final_score >= threshold:

            results.append({

                "report_id":
                    report.get("report_id"),

                "similarity":
                    round(final_score, 3),

                "distance_km":
                    round(distance, 2)
                    if distance is not None
                    else None,

                "reason":
                    "Text similarity and/or nearby location"
            })


    results.sort(
        key=lambda x: x["similarity"],
        reverse=True
    )

    return results


# =========================================
# FALLBACK SEVERITY
# =========================================

def severity_fallback(
    description,
    emergency_type=""
):

    text = (
        f"{description} {emergency_type}"
    ).lower()


    critical_words = [
        "trapped",
        "multiple casualties",
        "collapsed",
        "building collapse",
        "unconscious",
        "severe bleeding",
        "major fire",
        "people drowning",
        "drowning",
        "explosion",
        "mass casualty"
    ]


    high_words = [
        "injured",
        "injury",
        "fire",
        "flood",
        "accident",
        "danger",
        "evacuate",
        "heavy smoke"
    ]


    medium_words = [
        "water",
        "blocked road",
        "minor injury",
        "smoke",
        "damage"
    ]


    for word in critical_words:

        if word in text:

            return {
                "severity": "Critical",
                "severity_score": 95
            }


    for word in high_words:

        if word in text:

            return {
                "severity": "High",
                "severity_score": 75
            }


    for word in medium_words:

        if word in text:

            return {
                "severity": "Medium",
                "severity_score": 50
            }


    return {
        "severity": "Low",
        "severity_score": 25
    }


# =========================================
# RESOURCE MATCHING
# =========================================

def match_resources(
    incident,
    resources
):

    incident_type = (
        incident.get("emergency_type")
        or ""
    ).lower()

    description = (
        incident.get("description")
        or ""
    ).lower()


    recommendations = []


    for resource in resources:

        resource_type = (
            resource.get("resource_type")
            or ""
        ).lower()

        resource_status = (
            resource.get("status")
            or ""
        ).lower()


        if resource_status not in [
            "available",
            "ready",
            "standby"
        ]:

            continue


        score = 0

        rationale = []


        # Ambulance
        if (
            "medical" in incident_type
            or "accident" in incident_type
            or "injur" in description
        ):

            if "ambulance" in resource_type:

                score += 90

                rationale.append(
                    "Medical transport is relevant."
                )


        # Fire response
        if "fire" in incident_type:

            if (
                "fire" in resource_type
                or "fire truck" in resource_type
            ):

                score += 95

                rationale.append(
                    "Fire response capability matches incident."
                )


        # Flood
        if "flood" in incident_type:

            if (
                "rescue" in resource_type
                or "boat" in resource_type
            ):

                score += 90

                rationale.append(
                    "Flood rescue capability matches incident."
                )


        # Earthquake
        if "earthquake" in incident_type:

            if (
                "rescue" in resource_type
                or "search" in resource_type
            ):

                score += 90

                rationale.append(
                    "Search and rescue capability matches incident."
                )


        # Generic rescue
        if (
            "rescue" in resource_type
            and score == 0
        ):

            score += 45

            rationale.append(
                "General rescue capability available."
            )


        if score > 0:

            recommendations.append({

                "resource_id":
                    resource.get("id"),

                "resource_name":
                    resource.get("name"),

                "resource_type":
                    resource.get("resource_type"),

                "match_score":
                    score,

                "rationale":
                    " ".join(rationale)
            })


    recommendations.sort(
        key=lambda x: x["match_score"],
        reverse=True
    )

    return recommendations


# =========================================
# RESPONSE PLAN
# =========================================

def build_response_plan(
    incident
):

    severity = (
        incident.get("severity")
        or "Unknown"
    )

    emergency_type = (
        incident.get("emergency_type")
        or "Other"
    )


    actions = []


    if severity in [
        "Critical",
        "High"
    ]:

        actions.append(
            "Prioritize human verification immediately."
        )

        actions.append(
            "Notify the appropriate emergency response team."
        )

        actions.append(
            "Identify and assign suitable resources."
        )


    else:

        actions.append(
            "Review the incident details."
        )

        actions.append(
            "Verify location and reported impact."
        )


    if emergency_type == "Flood":

        actions.append(
            "Assess evacuation and water rescue requirements."
        )


    elif emergency_type == "Fire":

        actions.append(
            "Assess fire spread and evacuation risk."
        )


    elif emergency_type == "Earthquake":

        actions.append(
            "Check for structural damage and trapped persons."
        )


    elif emergency_type == "Road Accident":

        actions.append(
            "Prioritize medical assessment and traffic safety."
        )


    elif emergency_type == "Medical Emergency":

        actions.append(
            "Prioritize medical response and patient condition verification."
        )


    actions.append(
        "Record response decisions in the audit trail."
    )


    return actions
