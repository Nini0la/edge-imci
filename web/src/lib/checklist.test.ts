import { describe, expect, it } from "vitest";
import { buildChecklist } from "./checklist";
import type { AnalysisResult } from "../types";

describe("buildChecklist", () => {
  it("represents unreported findings as unknown, never absent", () => {
    const checklist = buildChecklist();

    expect(checklist.age.state).toBe("unknown");
    expect(checklist.sections.flatMap((section) => section.items).every((item) => item.state === "unknown")).toBe(true);
  });

  it("distinguishes explicit negatives from unknown findings", () => {
    const checklist = buildChecklist({
      patient_facts: {
        age_months: 18,
        has_cough_or_difficult_breathing: false,
        has_diarrhoea: null,
        has_fever: false,
        has_ear_problem: false,
      },
      danger_signs: {
        unable_to_drink_or_breastfeed: false,
        vomits_everything: null,
        had_convulsions: false,
        lethargic_or_unconscious: false,
        convulsing_now: false,
      },
    });

    const danger = checklist.sections.find((section) => section.id === "danger")!;
    expect(danger.items.find((item) => item.label === "Unable to drink or breastfeed")?.state).toBe("absent");
    expect(danger.items.find((item) => item.label === "Vomits everything")?.state).toBe("unknown");
  });

  it("uses urgent only when deterministic evidence identifies an urgent finding", () => {
    const encounter = {
      patient_facts: {},
      danger_signs: { convulsing_now: true },
    };
    const result = {
      is_urgent: true,
      decision_trace: [{ findings: [["Convulsing now", "Yes"]] }],
    } as unknown as AnalysisResult;

    const checklist = buildChecklist(encounter, result);
    const item = checklist.sections
      .find((section) => section.id === "danger")!
      .items.find((entry) => entry.label === "Convulsing now");

    expect(item?.state).toBe("urgent");
  });

  it("provides source-grounded procedural respiratory guidance", () => {
    const respiratory = buildChecklist().sections.find((section) => section.id === "respiratory")!;

    expect(respiratory.sourcePage).toBe(2);
    expect(respiratory.guidance.flatMap((guide) => guide.lines)).toContain(
      "Age 2-11 months: 50 breaths/minute or more",
    );
    expect(respiratory.guidance.flatMap((guide) => guide.lines)).toContain(
      "Age 12-59 months: 40 breaths/minute or more",
    );
    expect(respiratory.items.find((item) => item.label === "Full-minute count")?.instruction).toBe(
      "Count the breaths for one full minute.",
    );
    expect(respiratory.items.find((item) => item.label === "Child calm")?.method).toBe(
      "LOOK / LISTEN / FEEL",
    );
  });

  it("stops conditional checks after an explicit negative entry answer", () => {
    const respiratory = buildChecklist({
      patient_facts: { has_cough_or_difficult_breathing: false },
    }).sections.find((section) => section.id === "respiratory")!;

    expect(respiratory.inactive).toBe(true);
    expect(respiratory.items.map((item) => item.label)).toEqual(["Cough or difficult breathing"]);
  });

  it("reveals measles complication checks for current measles signs", () => {
    const fever = buildChecklist({
      patient_facts: { has_fever: true },
      fever: {
        generalized_rash: true,
        measles_cough: true,
        measles_within_last_3_months: false,
      },
    }).sections.find((section) => section.id === "fever")!;

    expect(fever.items.map((item) => item.label)).toContain("Clouding of cornea");
    expect(fever.items.map((item) => item.label)).toContain("Mouth ulcers");
  });

  it("represents the supported conditional evidence in the guide", () => {
    const itemIds = new Set(
      buildChecklist().sections.flatMap((section) => section.items.map((item) => item.id)),
    );

    [
      "respiratory.post_bronchodilator_child_calm",
      "respiratory.post_bronchodilator_breaths_counted_one_minute",
      "respiratory.hiv_exposed_or_infected",
      "diarrhoea.cholera_in_area",
      "fever.obvious_cause_of_fever_present",
      "fever.malaria_test_available",
      "fever.mouth_ulcers_deep_or_extensive",
    ].forEach((path) => expect(itemIds.has(path), path).toBe(true));
  });
});
