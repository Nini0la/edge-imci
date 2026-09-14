"""Optional transcript-only smoke check of an already-running frontier server.

Synthetic truths below are a test oracle, NOT a production auto-accept policy.
No ASR, authentication, environment files, retries, or diagnostic files are used.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from http.client import HTTPConnection
import json
import re
from time import perf_counter
from urllib.parse import urlsplit


PREREQUISITES_REPORT = (
    "The child is 18 months old. The child can drink or breastfeed, does not "
    "vomit everything, has had no convulsions during this illness, is not "
    "convulsing now, and is neither lethargic nor unconscious. "
    "No diarrhoea, no fever, and no ear problem."
)
PREREQUISITES = {
    "patient_facts.age_months": 18,
    "danger_signs.unable_to_drink_or_breastfeed": False,
    "danger_signs.vomits_everything": False,
    "danger_signs.had_convulsions": False,
    "danger_signs.convulsing_now": False,
    "danger_signs.lethargic_or_unconscious": False,
    "patient_facts.has_diarrhoea": False,
    "patient_facts.has_fever": False,
    "patient_facts.has_ear_problem": False,
}
ENGLISH_REPORT = (
    "The child has had a cough for 3 days. Respiratory rate is 52 breaths per "
    "minute, counted for one full minute while the child was calm. "
    "No chest indrawing, no wheezing, and no recurrent wheeze. "
    "No pulse oximeter is available."
)
YORUBA_REPORT = (
    "\u1eccm\u1ecd n\u00e1\u00e0 ti n k\u00f3 ik\u1ecd f\u00fan \u1ecdj\u1ecd m\u1eb9\u0301ta. "
    "Respiratory rate j\u1eb9\u0301 52 breaths per minute; mo k\u00e0 \u00e1 f\u00fan "
    "one full minute n\u00edgb\u00e0 t\u00ed \u1ecdm\u1ecd n\u00e1\u00e0 bal\u1eb9\u0300. "
    "K\u00f2 s\u00ed chest indrawing, k\u00f2 s\u00ed wheezing, "
    "k\u00f2 s\u00ed history of recurrent wheeze. "
    "A k\u00f2 n\u00ed pulse oximeter."
)
RESPIRATORY = {
    "patient_facts.has_cough_or_difficult_breathing": True,
    "respiratory.cough_duration_days": 3,
    "respiratory.respiratory_rate": 52,
    "respiratory.child_calm": True,
    "respiratory.breaths_counted_one_minute": True,
    "respiratory.chest_indrawing": False,
    "respiratory.wheezing": False,
    "respiratory.recurrent_wheeze": False,
    "respiratory.pulse_oximeter_available": False,
}
STRIDOR = "respiratory.stridor_when_calm"
VOMITING_REPORT = "The child is vomiting since yesterday"


def leaves(value, prefix=""):
    result = {}
    for name, item in value.items():
        path = f"{prefix}.{name}" if prefix else name
        if isinstance(item, dict):
            result.update(leaves(item, path))
        else:
            result[path] = item
    return result


def with_values(encounter, values):
    result = deepcopy(encounter)
    for field, value in values.items():
        section, name = field.split(".")
        result[section][name] = value
    return result


def require(condition, message):
    # Unlike Python assert, review gates must also run under python -O.
    if not condition:
        raise AssertionError(message)


def check_synthetic_proposal(preview, expected):
    """Reject unexpected fields/values before any synthetic review is submitted."""
    candidate = {key: value for key, value in leaves(preview["candidate_encounter"]).items()
                 if value is not None}
    changes = preview["changes"]
    require(len(changes) == len(expected), "Unexpected proposal count")
    require({row["field"] for row in changes} == set(expected), "Unexpected proposal fields")
    require(set(candidate) == set(expected), "Unexpected canonical fields")
    require(not preview["uncertainties"], "Unexpected uncertainty in explicit synthetic report")
    for row in changes:
        field, truth = row["field"], expected[row["field"]]
        require(type(row["value"]) is type(truth) and row["value"] == truth,
                "Unexpected proposed value")
        require(type(candidate[field]) is type(truth) and candidate[field] == truth,
                "Unexpected canonical value")
        require(not row["uncertain"], "Unexpected uncertain proposal")


def loopback_url(value):
    if not re.fullmatch(r"http://(?:127\.0\.0\.1|localhost):[0-9]{1,5}/?", value):
        raise argparse.ArgumentTypeError("Use http://127.0.0.1:PORT or http://localhost:PORT only.")
    if not 1 <= urlsplit(value).port <= 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535.")
    return value.rstrip("/")


def run_demo(base_url):
    started = perf_counter()
    counts = {"http_calls": 0, "scoped_provider_calls": 0}
    mode, stage = None, "health"

    def request(path, body=None):
        counts["http_calls"] += 1
        # Direct loopback connection: no proxy environment, DNS, or redirects.
        connection = HTTPConnection("127.0.0.1", urlsplit(base_url).port, timeout=90)
        try:
            data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
            connection.request("GET" if body is None else "POST", "/api/" + path,
                               body=data, headers={"Content-Type": "application/json"})
            with connection.getresponse() as response:
                require(response.status == 200, "HTTP request failed")
                return json.load(response)
        finally:
            connection.close()

    def extract(assessment, encounter, report, question_field=None):
        require(counts["scoped_provider_calls"] < 6, "Scoped call budget exhausted")
        counts["scoped_provider_calls"] += 1
        body = {"assessment": assessment, "encounter": encounter, "findings": report}
        if question_field is not None:
            body["question_field"] = question_field
        preview = request("assessment/extract", body)
        require(preview["extraction_mode"] == mode, "Scoped provider mode changed")
        require(preview["understanding"]["provider"] == "azure-openai", "Not frontier evidence")
        require(preview["input_text"] == report, "Original transcript not preserved")
        return preview

    def synthetic_review(assessment, encounter, preview, expected):
        check_synthetic_proposal(preview, expected)
        result = request("assessment/accept", {
            "assessment": assessment, "encounter": encounter, "confirmed": True,
            "changes": preview["changes"],
            "resolutions": {field: "replace" for field in expected},
        })
        require(result["encounter"] == with_values(encounter, expected), "Unexpected accepted evidence")
        return result

    try:
        health = request("health")
        require(health["status"] == "ok", "Server is not healthy")
        reported_mode = health["language_understanding"]["mode"]
        require(re.fullmatch(r"azure-openai/[A-Za-z0-9._-]+", reported_mode), "Server must use frontier mode")
        mode = reported_mode
        empty = request("assessment/evaluate", {})["encounter"]
        require(all(value is None for value in leaves(empty).values()), "Initial evidence is not empty")

        stage = "prerequisites"
        preview = extract("danger", empty, PREREQUISITES_REPORT)
        baseline = synthetic_review("danger", empty, preview, PREREQUISITES)["encounter"]
        require(baseline["patient_facts"]["has_cough_or_difficult_breathing"] is None,
                "Respiratory entry was hallucinated")
        require(all(value is None for value in baseline["respiratory"].values()),
                "Respiratory observations were hallucinated")

        expected_final = with_values(baseline, {**RESPIRATORY, STRIDOR: False})
        reference = request("assessment/evaluate", {"encounter": expected_final})
        require(reference["analysis"]["classifications"] == ["Pneumonia"], "Unexpected reference classification")
        require(reference["analysis"]["state"] == "COMPLETE", "Reference is incomplete")
        results = []
        for language, report, answer in (
            ("english", ENGLISH_REPORT, "No"),
            ("yoruba-english", YORUBA_REPORT, "R\u00e1r\u00e1, k\u00f2 s\u00ed."),
        ):
            stage = language + "-respiratory"
            preview = extract("respiratory", deepcopy(baseline), report)
            partial = synthetic_review("respiratory", baseline, preview, RESPIRATORY)
            progress = partial["assessments"]["respiratory"]
            require(progress["status"] == "INCOMPLETE", "Missing stridor completed assessment")
            require(progress["missing_fields"] == [STRIDOR], "Unexpected missing respiratory fields")
            require(progress["question"] == {"field": STRIDOR, "text": "Is there stridor when the child is calm?"},
                    "Deterministic stridor question is not authoritative")
            stage = language + "-followup"
            preview = extract("respiratory", partial["encounter"], answer, STRIDOR)
            final = synthetic_review("respiratory", partial["encounter"], preview, {STRIDOR: False})
            require(final["encounter"] == expected_final, "Unexpected final canonical encounter")
            require(all(item["status"] == "COMPLETE" for item in final["assessments"].values()),
                    "Assessments did not complete")
            # Referral is represented by actions/urgency, not a separate API field.
            for key in ("state", "is_complete", "is_urgent", "classifications", "urgent_actions",
                        "final_actions", "deferred_actions", "missing_elements", "contradictions"):
                require(final["analysis"][key] == reference["analysis"][key], "Clinical result differs from reference")
            results.append(final["analysis"])
        require(results[0] == results[1], "Language variants changed deterministic output")

        stage = "ambiguity"
        preview = extract("danger", empty, VOMITING_REPORT)
        require(all(value is None for value in leaves(preview["candidate_encounter"]).values()),
                "Vomiting or relative time became unsupported canonical evidence")
        uncertainty = preview["uncertainties"]
        require(any(row["field"] == "danger_signs.vomits_everything" for row in uncertainty),
                "Vomiting ambiguity was not flagged")
        require(any("since yesterday" in row["source_text"] for row in uncertainty),
                "Relative duration ambiguity was not preserved")
        require(all(row["value"] is None and row["uncertain"] for row in preview["changes"]),
                "Ambiguity produced a known observation")
        require(any(row["field"] == "danger_signs.vomits_everything" for row in preview["changes"]),
                "Missing uncertainty review row")
        require(counts["scoped_provider_calls"] == 6, "Unexpected scoped call count")
        status = "passed"
    except Exception:
        # Never print provider bodies, raw prompts, credentials, or tracebacks.
        status = "failed"
    return {"status": status, "stage": stage, "transcript_only": True,
            "provider": mode, **counts, "latency_seconds": round(perf_counter() - started, 3)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", type=loopback_url, default="http://127.0.0.1:8000",
                        help="Existing local HTTP server (default: %(default)s).")
    parser.add_argument("--live", action="store_true",
                        help="Authorize up to six scoped frontier calls, which may incur charges.")
    args = parser.parse_args(argv)
    if not args.live:
        parser.error("--live is required to make calls; this is transcript-only, not an ASR test.")
    summary = run_demo(args.base_url)
    print(json.dumps(summary))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
