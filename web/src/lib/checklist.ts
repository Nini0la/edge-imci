import type { AnalysisResult } from "../types";

export type ChecklistState = "present" | "absent" | "unknown" | "urgent";
export type SectionCompletion = "pending" | "complete" | "incomplete";
export type AssessmentMethod = "ASK" | "LOOK / LISTEN / FEEL" | "MEASURE" | "IF INDICATED";

export interface ChecklistItem {
  id: string;
  label: string;
  instruction: string;
  method: AssessmentMethod;
  value: string;
  state: ChecklistState;
  conditional: boolean;
  note?: string;
}

export interface AssessmentGuidance {
  title: string;
  lines: string[];
  emphasis?: "calm" | "threshold" | "conditional";
}

export interface ChecklistSection {
  id: string;
  label: string;
  prompt: string;
  sourcePage: number;
  items: ChecklistItem[];
  guidance: AssessmentGuidance[];
  state: ChecklistState;
  completion: SectionCompletion;
  inactive: boolean;
}

type FieldDefinition = {
  path: string;
  label: string;
  instruction: string;
  method: AssessmentMethod;
  trueLabel?: string;
  falseLabel?: string;
  urgentEligible?: boolean;
  when?: [string, unknown];
  whenPredicate?: (encounter: Record<string, unknown>) => boolean;
  note?: string;
};

type SectionDefinition = {
  id: string;
  label: string;
  prompt: string;
  sourcePage: number;
  entryPath?: string;
  fields: FieldDefinition[];
  guidance?: AssessmentGuidance[];
};

const sectionDefinitions: SectionDefinition[] = [
  {
    id: "danger",
    label: "General danger signs",
    prompt: "Check every sick child for all five general danger signs.",
    sourcePage: 1,
    fields: [
      {
        path: "danger_signs.unable_to_drink_or_breastfeed",
        label: "Unable to drink or breastfeed",
        instruction: "Ask whether the child is able to drink or breastfeed.",
        method: "ASK",
        trueLabel: "Unable",
        falseLabel: "Able",
        urgentEligible: true,
      },
      {
        path: "danger_signs.vomits_everything",
        label: "Vomits everything",
        instruction: "Ask whether the child vomits everything.",
        method: "ASK",
        urgentEligible: true,
      },
      {
        path: "danger_signs.had_convulsions",
        label: "Convulsions during this illness",
        instruction: "Ask whether the child has had convulsions during this illness.",
        method: "ASK",
        urgentEligible: true,
      },
      {
        path: "danger_signs.lethargic_or_unconscious",
        label: "Lethargic or unconscious",
        instruction: "See whether the child is lethargic or unconscious.",
        method: "LOOK / LISTEN / FEEL",
        urgentEligible: true,
      },
      {
        path: "danger_signs.convulsing_now",
        label: "Convulsing now",
        instruction: "See whether the child is convulsing now.",
        method: "LOOK / LISTEN / FEEL",
        urgentEligible: true,
      },
    ],
    guidance: [
      {
        title: "Do not stop the assessment",
        lines: ["Any known danger sign requires urgent attention, but complete the remaining assessment rapidly."],
        emphasis: "conditional",
      },
    ],
  },
  {
    id: "respiratory",
    label: "Cough / difficult breathing",
    prompt: "Does the child have cough or difficult breathing?",
    sourcePage: 2,
    entryPath: "patient_facts.has_cough_or_difficult_breathing",
    fields: [
      {
        path: "patient_facts.has_cough_or_difficult_breathing",
        label: "Cough or difficult breathing",
        instruction: "Ask whether the child has cough or difficult breathing.",
        method: "ASK",
      },
      {
        path: "respiratory.cough_duration_days",
        label: "Cough duration",
        instruction: "If yes, ask for how long.",
        method: "ASK",
        when: ["patient_facts.has_cough_or_difficult_breathing", true],
      },
      {
        path: "respiratory.recurrent_wheeze",
        label: "Recurrent wheeze",
        instruction: "Ask whether wheezing has happened repeatedly.",
        method: "ASK",
        when: ["patient_facts.has_cough_or_difficult_breathing", true],
      },
      {
        path: "respiratory.child_calm",
        label: "Child calm",
        instruction: "Settle the child and confirm the child is calm before assessing breathing.",
        method: "LOOK / LISTEN / FEEL",
        trueLabel: "Calm",
        falseLabel: "Not calm",
        when: ["patient_facts.has_cough_or_difficult_breathing", true],
      },
      {
        path: "respiratory.chest_indrawing",
        label: "Chest indrawing",
        instruction: "Look for chest indrawing.",
        method: "LOOK / LISTEN / FEEL",
        urgentEligible: true,
        when: ["patient_facts.has_cough_or_difficult_breathing", true],
      },
      {
        path: "respiratory.stridor_when_calm",
        label: "Stridor when calm",
        instruction: "Look and listen for stridor while the child is calm.",
        method: "LOOK / LISTEN / FEEL",
        urgentEligible: true,
        when: ["patient_facts.has_cough_or_difficult_breathing", true],
      },
      {
        path: "respiratory.wheezing",
        label: "Wheezing",
        instruction: "Look and listen for wheezing.",
        method: "LOOK / LISTEN / FEEL",
        when: ["patient_facts.has_cough_or_difficult_breathing", true],
      },
      {
        path: "respiratory.breaths_counted_one_minute",
        label: "Full-minute count",
        instruction: "Count the breaths for one full minute.",
        method: "MEASURE",
        trueLabel: "Full minute",
        falseLabel: "Invalid count",
        when: ["patient_facts.has_cough_or_difficult_breathing", true],
      },
      {
        path: "respiratory.respiratory_rate",
        label: "Respiratory rate",
        instruction: "Record the respiratory rate in breaths per minute.",
        method: "MEASURE",
        when: ["patient_facts.has_cough_or_difficult_breathing", true],
      },
      {
        path: "respiratory.pulse_oximeter_available",
        label: "Pulse oximeter availability",
        instruction: "If available, use a pulse oximeter.",
        method: "IF INDICATED",
        trueLabel: "Available",
        falseLabel: "Unavailable",
        when: ["patient_facts.has_cough_or_difficult_breathing", true],
      },
      {
        path: "respiratory.oxygen_saturation_percent",
        label: "Oxygen saturation",
        instruction: "Record oxygen saturation when pulse oximetry is available.",
        method: "IF INDICATED",
        when: ["respiratory.pulse_oximeter_available", true],
      },
      {
        path: "respiratory.bronchodilator_trial_completed",
        label: "Bronchodilator trial",
        instruction: "If wheezing occurs with fast breathing or chest indrawing, give the indicated rapid-acting bronchodilator trial.",
        method: "IF INDICATED",
        whenPredicate: needsBronchodilatorTrial,
      },
      {
        path: "respiratory.post_bronchodilator_respiratory_rate",
        label: "Post-bronchodilator rate",
        instruction: "After the trial, record the new respiratory rate.",
        method: "IF INDICATED",
        when: ["respiratory.bronchodilator_trial_completed", true],
      },
      {
        path: "respiratory.post_bronchodilator_child_calm",
        label: "Calm after bronchodilator",
        instruction: "Settle the child again and confirm the child is calm before reassessment.",
        method: "IF INDICATED",
        trueLabel: "Calm",
        falseLabel: "Not calm",
        when: ["respiratory.bronchodilator_trial_completed", true],
      },
      {
        path: "respiratory.post_bronchodilator_breaths_counted_one_minute",
        label: "Post-bronchodilator full-minute count",
        instruction: "Repeat the respiratory count for one full minute.",
        method: "IF INDICATED",
        trueLabel: "Full minute",
        falseLabel: "Invalid count",
        when: ["respiratory.bronchodilator_trial_completed", true],
      },
      {
        path: "respiratory.post_bronchodilator_chest_indrawing",
        label: "Post-bronchodilator chest indrawing",
        instruction: "Look again for chest indrawing after the bronchodilator trial.",
        method: "IF INDICATED",
        when: ["respiratory.bronchodilator_trial_completed", true],
      },
      {
        path: "respiratory.hiv_exposed_or_infected",
        label: "HIV exposure or infection",
        instruction: "If chest indrawing persists, establish whether the child is HIV exposed or infected.",
        method: "IF INDICATED",
        whenPredicate: hasEffectiveChestIndrawing,
      },
    ],
    guidance: [
      {
        title: "Child must be calm",
        lines: ["A respiratory rate or calm-state sign is not valid when the child is unsettled."],
        emphasis: "calm",
      },
      {
        title: "Fast-breathing reference",
        lines: [
          "Age 2-11 months: 50 breaths/minute or more",
          "Age 12-59 months: 40 breaths/minute or more",
        ],
        emphasis: "threshold",
      },
    ],
  },
  {
    id: "diarrhoea",
    label: "Diarrhoea",
    prompt: "Does the child have diarrhoea?",
    sourcePage: 3,
    entryPath: "patient_facts.has_diarrhoea",
    fields: [
      {
        path: "patient_facts.has_diarrhoea",
        label: "Diarrhoea",
        instruction: "Ask whether the child has diarrhoea.",
        method: "ASK",
      },
      {
        path: "diarrhoea.duration_days",
        label: "Diarrhoea duration",
        instruction: "If yes, ask for how long.",
        method: "ASK",
        when: ["patient_facts.has_diarrhoea", true],
      },
      {
        path: "diarrhoea.blood_in_stool",
        label: "Blood in stool",
        instruction: "Ask whether there is blood in the stool.",
        method: "ASK",
        when: ["patient_facts.has_diarrhoea", true],
      },
      {
        path: "diarrhoea.dehydration.restless_or_irritable",
        label: "Restless or irritable",
        instruction: "Look at the child's general condition: restless or irritable?",
        method: "LOOK / LISTEN / FEEL",
        when: ["patient_facts.has_diarrhoea", true],
      },
      {
        path: "danger_signs.lethargic_or_unconscious",
        label: "Lethargic or unconscious",
        instruction: "Look at the child's general condition: lethargic or unconscious?",
        method: "LOOK / LISTEN / FEEL",
        urgentEligible: true,
        when: ["patient_facts.has_diarrhoea", true],
      },
      {
        path: "diarrhoea.dehydration.sunken_eyes",
        label: "Sunken eyes",
        instruction: "Look for sunken eyes.",
        method: "LOOK / LISTEN / FEEL",
        when: ["patient_facts.has_diarrhoea", true],
      },
      {
        path: "diarrhoea.dehydration.drinking_status",
        label: "Drinking status",
        instruction: "Offer fluid and observe whether the child cannot drink, drinks poorly, or drinks eagerly and thirstily.",
        method: "LOOK / LISTEN / FEEL",
        when: ["patient_facts.has_diarrhoea", true],
      },
      {
        path: "diarrhoea.dehydration.skin_pinch",
        label: "Skin pinch",
        instruction: "Pinch the abdominal skin and observe whether it returns normally, slowly, or very slowly.",
        method: "LOOK / LISTEN / FEEL",
        note: "Very slowly means longer than 2 seconds.",
        when: ["patient_facts.has_diarrhoea", true],
      },
      {
        path: "diarrhoea.cholera_in_area",
        label: "Cholera in area",
        instruction: "For severe dehydration in a child age 2 years or older, establish whether cholera is present in the area.",
        method: "IF INDICATED",
        whenPredicate: hasSevereDehydrationInOlderChild,
      },
    ],
  },
  {
    id: "fever",
    label: "Fever, including measles",
    prompt: "Does the child have fever by history, feel, or measured temperature?",
    sourcePage: 4,
    entryPath: "patient_facts.has_fever",
    fields: [
      {
        path: "patient_facts.has_fever",
        label: "Fever",
        instruction: "Ask about fever history and determine whether the child feels hot.",
        method: "ASK",
      },
      {
        path: "fever.fever_duration_days",
        label: "Fever duration",
        instruction: "If yes, ask for how long.",
        method: "ASK",
        when: ["patient_facts.has_fever", true],
      },
      {
        path: "fever.fever_present_every_day",
        label: "Fever every day",
        instruction: "If fever has lasted more than 7 days, ask whether it has been present every day.",
        method: "ASK",
        whenPredicate: (encounter) => Number(getValue(encounter, "fever.fever_duration_days")) > 7,
      },
      {
        path: "fever.measles_within_last_3_months",
        label: "Measles in last 3 months",
        instruction: "Ask whether the child has had measles within the last 3 months.",
        method: "ASK",
        when: ["patient_facts.has_fever", true],
      },
      {
        path: "fever.malaria_risk",
        label: "Malaria risk",
        instruction: "Establish the local malaria-risk category; do not infer it.",
        method: "ASK",
        when: ["patient_facts.has_fever", true],
      },
      {
        path: "fever.stiff_neck",
        label: "Stiff neck",
        instruction: "Look or feel for stiff neck.",
        method: "LOOK / LISTEN / FEEL",
        urgentEligible: true,
        when: ["patient_facts.has_fever", true],
      },
      {
        path: "fever.runny_nose",
        label: "Runny nose",
        instruction: "Look for runny nose.",
        method: "LOOK / LISTEN / FEEL",
        when: ["patient_facts.has_fever", true],
      },
      {
        path: "fever.identified_bacterial_cause_present",
        label: "Bacterial cause of fever",
        instruction: "Look for an identifiable bacterial cause of fever.",
        method: "LOOK / LISTEN / FEEL",
        when: ["patient_facts.has_fever", true],
      },
      {
        path: "fever.obvious_cause_of_fever_present",
        label: "Obvious cause of fever",
        instruction: "Determine whether another obvious cause of fever is present.",
        method: "LOOK / LISTEN / FEEL",
        when: ["patient_facts.has_fever", true],
      },
      {
        path: "fever.generalized_rash",
        label: "Generalized rash",
        instruction: "Look for generalized rash as part of the measles assessment.",
        method: "LOOK / LISTEN / FEEL",
        when: ["patient_facts.has_fever", true],
      },
      {
        path: "fever.measles_cough",
        label: "Cough with rash",
        instruction: "With generalized rash, establish whether cough is present.",
        method: "LOOK / LISTEN / FEEL",
        when: ["patient_facts.has_fever", true],
      },
      {
        path: "fever.red_eyes",
        label: "Red eyes",
        instruction: "With generalized rash, look for red eyes.",
        method: "LOOK / LISTEN / FEEL",
        when: ["patient_facts.has_fever", true],
      },
      {
        path: "fever.temperature_c",
        label: "Axillary temperature",
        instruction: "Measure and record axillary temperature when available.",
        method: "MEASURE",
        when: ["patient_facts.has_fever", true],
      },
      {
        path: "fever.malaria_test_available",
        label: "Malaria test availability",
        instruction: "When a malaria test is required, establish whether a test is available.",
        method: "IF INDICATED",
        trueLabel: "Available",
        falseLabel: "Unavailable",
        when: ["patient_facts.has_fever", true],
      },
      {
        path: "fever.malaria_test_result",
        label: "Malaria test result",
        instruction: "Perform a malaria test when required by malaria risk and the absence of severe classification.",
        method: "IF INDICATED",
        when: ["fever.malaria_test_available", true],
      },
      {
        path: "fever.mouth_ulcers",
        label: "Mouth ulcers",
        instruction: "If measles is current or recent, look for mouth ulcers.",
        method: "IF INDICATED",
        whenPredicate: hasCurrentOrRecentMeasles,
      },
      {
        path: "fever.mouth_ulcers_deep_or_extensive",
        label: "Deep or extensive mouth ulcers",
        instruction: "If mouth ulcers are present, determine whether they are deep or extensive.",
        method: "IF INDICATED",
        when: ["fever.mouth_ulcers", true],
      },
      {
        path: "fever.pus_draining_from_eye",
        label: "Pus draining from eye",
        instruction: "If measles is current or recent, look for pus draining from the eye.",
        method: "IF INDICATED",
        whenPredicate: hasCurrentOrRecentMeasles,
      },
      {
        path: "fever.clouding_of_cornea",
        label: "Clouding of cornea",
        instruction: "If measles is current or recent, look for clouding of the cornea.",
        method: "IF INDICATED",
        urgentEligible: true,
        whenPredicate: hasCurrentOrRecentMeasles,
      },
    ],
    guidance: [
      {
        title: "Fever reference",
        lines: ["The source fever entry threshold is axillary temperature 37.5 C or above."],
        emphasis: "threshold",
      },
    ],
  },
  {
    id: "ear",
    label: "Ear problem",
    prompt: "Does the child have an ear problem?",
    sourcePage: 5,
    entryPath: "patient_facts.has_ear_problem",
    fields: [
      {
        path: "patient_facts.has_ear_problem",
        label: "Ear problem",
        instruction: "Ask whether the child has an ear problem.",
        method: "ASK",
      },
      {
        path: "ear.ear_pain",
        label: "Ear pain",
        instruction: "If yes, ask whether there is ear pain.",
        method: "ASK",
        when: ["patient_facts.has_ear_problem", true],
      },
      {
        path: "ear.ear_discharge_reported",
        label: "Ear discharge",
        instruction: "Ask whether there is ear discharge.",
        method: "ASK",
        when: ["patient_facts.has_ear_problem", true],
      },
      {
        path: "ear.ear_discharge_duration_days",
        label: "Discharge duration",
        instruction: "If discharge is reported, ask for how long.",
        method: "ASK",
        when: ["ear.ear_discharge_reported", true],
      },
      {
        path: "ear.pus_draining_from_ear",
        label: "Pus draining from ear",
        instruction: "Look for pus draining from the ear.",
        method: "LOOK / LISTEN / FEEL",
        when: ["patient_facts.has_ear_problem", true],
      },
      {
        path: "ear.tender_swelling_behind_ear",
        label: "Tender swelling behind ear",
        instruction: "Feel for tender swelling behind the ear.",
        method: "LOOK / LISTEN / FEEL",
        urgentEligible: true,
        when: ["patient_facts.has_ear_problem", true],
      },
    ],
  },
];

function getValue(encounter: Record<string, unknown> | undefined, path: string): unknown {
  let value: unknown = encounter;
  for (const part of path.split(".")) {
    if (!value || typeof value !== "object") return undefined;
    value = (value as Record<string, unknown>)[part];
  }
  return value;
}

function hasValidFastBreathing(encounter: Record<string, unknown>): boolean {
  if (getValue(encounter, "respiratory.child_calm") !== true) return false;
  if (getValue(encounter, "respiratory.breaths_counted_one_minute") !== true) return false;
  const age = Number(getValue(encounter, "patient_facts.age_months"));
  const rate = Number(getValue(encounter, "respiratory.respiratory_rate"));
  if (!Number.isFinite(age) || !Number.isFinite(rate)) return false;
  return age >= 2 && age < 12 ? rate >= 50 : age >= 12 && age < 60 && rate >= 40;
}

function needsBronchodilatorTrial(encounter: Record<string, unknown>): boolean {
  if (getValue(encounter, "respiratory.wheezing") !== true) return false;
  const validChestIndrawing = getValue(encounter, "respiratory.child_calm") === true
    && getValue(encounter, "respiratory.chest_indrawing") === true;
  return validChestIndrawing || hasValidFastBreathing(encounter);
}

function hasEffectiveChestIndrawing(encounter: Record<string, unknown>): boolean {
  if (getValue(encounter, "respiratory.chest_indrawing") !== true) return false;
  if (!needsBronchodilatorTrial(encounter)) return getValue(encounter, "respiratory.child_calm") === true;
  return getValue(encounter, "respiratory.bronchodilator_trial_completed") === true
    && getValue(encounter, "respiratory.post_bronchodilator_child_calm") === true
    && getValue(encounter, "respiratory.post_bronchodilator_chest_indrawing") === true;
}

function hasSevereDehydrationInOlderChild(encounter: Record<string, unknown>): boolean {
  if (Number(getValue(encounter, "patient_facts.age_months")) < 24) return false;
  const severeSigns = [
    getValue(encounter, "danger_signs.lethargic_or_unconscious") === true,
    getValue(encounter, "diarrhoea.dehydration.sunken_eyes") === true,
    ["UNABLE", "POORLY"].includes(String(getValue(encounter, "diarrhoea.dehydration.drinking_status"))),
    getValue(encounter, "diarrhoea.dehydration.skin_pinch") === "VERY_SLOWLY",
  ];
  return severeSigns.filter(Boolean).length >= 2;
}

function hasCurrentOrRecentMeasles(encounter: Record<string, unknown>): boolean {
  if (getValue(encounter, "fever.measles_within_last_3_months") === true) return true;
  if (getValue(encounter, "fever.generalized_rash") !== true) return false;
  return getValue(encounter, "fever.measles_cough") === true
    || getValue(encounter, "fever.runny_nose") === true
    || getValue(encounter, "fever.red_eyes") === true;
}

function displayValue(value: unknown, field: FieldDefinition): string {
  if (value === undefined || value === null) return "Unknown";
  if (typeof value === "boolean") {
    return value ? field.trueLabel ?? "Present" : field.falseLabel ?? "Absent";
  }
  if (field.path === "patient_facts.age_months") return `${value} months`;
  if (field.path.endsWith("duration_days")) return `${value} days`;
  if (field.path.endsWith("temperature_c")) return `${value} C`;
  if (field.path.endsWith("respiratory_rate")) return `${value} / min`;
  if (field.path.endsWith("oxygen_saturation_percent")) return `${value}%`;
  return String(value).replaceAll("_", " ").toLowerCase();
}

export function buildChecklist(
  encounter?: Record<string, unknown>,
  result?: AnalysisResult | null,
): { age: ChecklistItem; sections: ChecklistSection[] } {
  const urgentLabels = new Set(
    result?.is_urgent
      ? result.decision_trace.flatMap((trace) => trace.findings.map(([label]) => label))
      : [],
  );

  const createItem = (field: FieldDefinition, conditional = false): ChecklistItem => {
    const value = getValue(encounter, field.path);
    let state: ChecklistState = "present";
    if (value === undefined || value === null) state = "unknown";
    else if (value === false) state = "absent";
    if (field.urgentEligible && value === true && urgentLabels.has(field.label)) state = "urgent";
    return {
      id: field.path,
      label: field.label,
      instruction: field.instruction,
      method: field.method,
      value: displayValue(value, field),
      state,
      conditional,
      note: field.note,
    };
  };

  const sections = sectionDefinitions.map((section) => {
    const entryValue = section.entryPath ? getValue(encounter, section.entryPath) : undefined;
    const unresolvedEntry = Boolean(
      section.entryPath && (entryValue === undefined || entryValue === null),
    );
    const inactive = Boolean(encounter && section.entryPath && entryValue === false);
    const fields = section.fields.filter((field) => {
      if (!encounter) return true;
      if (unresolvedEntry) return true;
      if (field.whenPredicate) return field.whenPredicate(encounter);
      if (!field.when) return true;
      return getValue(encounter, field.when[0]) === field.when[1];
    });
    const items = fields.map((field) => createItem(
      field,
      unresolvedEntry && field.path !== section.entryPath,
    ));
    const state: ChecklistState = items.some((item) => item.state === "urgent")
      ? "urgent"
      : items.some((item) => item.state === "unknown")
        ? "unknown"
        : items.some((item) => item.state === "present")
          ? "present"
          : "absent";
    const completion: SectionCompletion = !encounter
      ? "pending"
      : items.some((item) => item.state === "unknown")
        ? "incomplete"
        : "complete";
    return {
      id: section.id,
      label: section.label,
      prompt: section.prompt,
      sourcePage: section.sourcePage,
      items,
      guidance: section.guidance ?? [],
      state,
      completion,
      inactive,
    };
  });

  return {
    age: createItem({
      path: "patient_facts.age_months",
      label: "Child age",
      instruction: "Confirm the child's age in completed months.",
      method: "ASK",
    }),
    sections,
  };
}
