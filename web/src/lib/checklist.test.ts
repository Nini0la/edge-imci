import { describe, expect, it } from "vitest";
import { acceptedSectionFields, buildChecklist } from "./checklist";
import type { AnalysisResult } from "../types";

describe("accepted evidence review", () => {
  it("includes known evidence hidden by negative pathway entries, including false and zero", () => {
    const encounter = {
      patient_facts: { age_months: 24, has_ear_problem: false },
      ear: { ear_pain: true, ear_discharge_duration_days: 0, tender_swelling_behind_ear: null },
    };
    const fields = acceptedSectionFields(encounter, "ear");
    expect(fields.map((field) => [field.field, field.previous])).toEqual([
      ["patient_facts.age_months", 24], ["patient_facts.has_ear_problem", false],
      ["ear.ear_pain", true], ["ear.ear_discharge_duration_days", 0],
    ]);
    expect(fields.every((field) => field.value === null && field.conflict && !field.outside_assessment)).toBe(true);
    expect(encounter.ear.ear_pain).toBe(true);
  });

  it("offers shared age and the permitted diarrhoea danger observation, without unrelated fields", () => {
    const encounter = { patient_facts: { age_months: 24 }, danger_signs: { lethargic_or_unconscious: true, convulsing_now: true }, ear: { ear_pain: true } };
    expect(acceptedSectionFields(encounter, "diarrhoea").map((field) => field.field)).toEqual([
      "patient_facts.age_months", "danger_signs.lethargic_or_unconscious",
    ]);
    expect(acceptedSectionFields(encounter, "danger").map((field) => field.field)).toContain("danger_signs.convulsing_now");
    expect(acceptedSectionFields({}, "ear")).toEqual([]);
  });
});

describe("buildChecklist", () => {
  it("represents unreported findings as unknown, never absent", () => {
    const checklist = buildChecklist();

    expect(checklist.age.state).toBe("unknown");
    expect(checklist.sections.flatMap((section) => section.items).every((item) => item.state === "unknown")).toBe(true);
    expect(checklist.sections.every((section) => section.completion === "pending")).toBe(true);
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
    expect(danger.completion).toBe("incomplete");
    expect(checklist.sections.find((section) => section.id === "respiratory")?.completion).toBe("complete");
    expect(checklist.sections.find((section) => section.id === "diarrhoea")?.completion).toBe("incomplete");
    expect(checklist.sections.find((section) => section.id === "fever")?.completion).toBe("complete");
    expect(checklist.sections.find((section) => section.id === "ear")?.completion).toBe("complete");
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

  it("shows the full conditional pathway while an entry answer is unknown", () => {
    const diarrhoea = buildChecklist({
      patient_facts: { has_diarrhoea: null },
      diarrhoea: null,
    }).sections.find((section) => section.id === "diarrhoea")!;

    expect(diarrhoea.inactive).toBe(false);
    expect(diarrhoea.completion).toBe("incomplete");
    expect(diarrhoea.items.map((item) => item.label)).toEqual(expect.arrayContaining([
      "Diarrhoea",
      "Diarrhoea duration",
      "Blood in stool",
      "Sunken eyes",
      "Skin pinch",
    ]));
    expect(diarrhoea.items.find((item) => item.label === "Diarrhoea")?.conditional).toBe(false);
    expect(
      diarrhoea.items
        .filter((item) => item.label !== "Diarrhoea")
        .every((item) => item.conditional),
    ).toBe(true);
  });

  it("shows only applicable non-conditional prompts after a positive entry answer", () => {
    const diarrhoea = buildChecklist({
      patient_facts: { has_diarrhoea: true },
      diarrhoea: {
        duration_days: null,
        blood_in_stool: null,
        dehydration: {},
      },
    }).sections.find((section) => section.id === "diarrhoea")!;

    expect(diarrhoea.inactive).toBe(false);
    expect(diarrhoea.completion).toBe("incomplete");
    expect(diarrhoea.items.length).toBeGreaterThan(1);
    expect(diarrhoea.items.every((item) => !item.conditional)).toBe(true);
  });

  it("marks a fully documented positive branch complete", () => {
    const diarrhoea = buildChecklist({
      patient_facts: { age_months: 18, has_diarrhoea: true },
      danger_signs: { lethargic_or_unconscious: false },
      diarrhoea: {
        duration_days: 3,
        blood_in_stool: false,
        dehydration: {
          restless_or_irritable: false,
          sunken_eyes: false,
          drinking_status: "NORMAL",
          skin_pinch: "NORMAL",
        },
      },
    }).sections.find((section) => section.id === "diarrhoea")!;

    expect(diarrhoea.completion).toBe("complete");
    expect(diarrhoea.items.map((item) => item.label)).not.toContain("Cholera in area");
    expect(diarrhoea.items.every((item) => item.state !== "unknown")).toBe(true);
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

  it("collapses unknown entries in interactive mode without hiding universal danger checks", () => {
    const checklist = buildChecklist(undefined, null, { interactive: true });
    expect(checklist.sections.find((section) => section.id === "danger")?.items).toHaveLength(5);
    for (const section of checklist.sections.filter((section) => section.id !== "danger")) {
      expect(section.items).toHaveLength(1);
      expect(section.items[0].state).toBe("unknown");
      expect(section.items[0].conditional).toBe(false);
    }
  });

  it("reveals the normal positive branch from the working preview", () => {
    const respiratory = buildChecklist({
      patient_facts: { has_cough_or_difficult_breathing: true },
      respiratory: { wheezing: true, child_calm: true, chest_indrawing: true },
    }, null, { interactive: true }).sections.find((section) => section.id === "respiratory")!;
    expect(respiratory.items.map((item) => item.id)).toEqual(expect.arrayContaining([
      "respiratory.cough_duration_days", "respiratory.respiratory_rate", "respiratory.bronchodilator_trial_completed",
    ]));
    expect(respiratory.items.map((item) => item.id)).not.toContain("respiratory.oxygen_saturation_percent");
    expect(respiratory.items.every((item) => !item.conditional)).toBe(true);
  });

  it.each([null, false, true])("retains hidden known and pending observations with entry %s", (entry) => {
    const respiratory = buildChecklist({
      patient_facts: { has_cough_or_difficult_breathing: entry },
      respiratory: {
        oxygen_saturation_percent: 0,
        post_bronchodilator_chest_indrawing: false,
        post_bronchodilator_child_calm: null,
      },
    }, null, {
      interactive: true,
      pendingFields: ["respiratory.post_bronchodilator_child_calm"],
    }).sections.find((section) => section.id === "respiratory")!;
    expect(respiratory.items.map((item) => item.id)).toEqual(expect.arrayContaining([
      "respiratory.oxygen_saturation_percent", "respiratory.post_bronchodilator_chest_indrawing",
      "respiratory.post_bronchodilator_child_calm",
    ]));
    if (entry !== true) expect(respiratory.items).toHaveLength(4);
  });

  it.each([null, false])("does not reopen unknown required children when entry is %s", (entry) => {
    const respiratory = buildChecklist({
      patient_facts: { has_cough_or_difficult_breathing: entry },
      respiratory: { child_calm: null, post_bronchodilator_child_calm: null },
    }, null, {
      interactive: true,
      requiredFields: ["respiratory.child_calm", "respiratory.post_bronchodilator_child_calm"],
    }).sections.find((section) => section.id === "respiratory")!;
    expect(respiratory.items.map((item) => item.id)).toEqual(["patient_facts.has_cough_or_difficult_breathing"]);
  });

  it("forces server-required post-bronchodilator definitions despite local conditions", () => {
    const requiredFields = [
      "respiratory.post_bronchodilator_respiratory_rate",
      "respiratory.post_bronchodilator_child_calm",
      "respiratory.post_bronchodilator_breaths_counted_one_minute",
      "respiratory.post_bronchodilator_chest_indrawing",
      "respiratory.hiv_exposed_or_infected",
    ];
    const encounter = { patient_facts: { has_cough_or_difficult_breathing: true } };
    const ids = (interactive: boolean) => buildChecklist(encounter, null, { interactive, requiredFields })
      .sections.find((section) => section.id === "respiratory")!.items.map((item) => item.id);
    expect(ids(true)).toEqual(expect.arrayContaining(requiredFields));
    expect(ids(false)).not.toEqual(expect.arrayContaining(requiredFields));
    expect(ids(true)).not.toContain("respiratory.oxygen_saturation_percent");
    expect(new Set(ids(true)).size).toBe(ids(true).length);
  });
});
