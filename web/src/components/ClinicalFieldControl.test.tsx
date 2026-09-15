import { Children, isValidElement, type KeyboardEvent, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { ClinicalFieldControl, type ClinicalFieldControlProps } from "./ClinicalFieldControl";

type ElementProps = {
  children?: ReactNode;
  role?: string;
  value?: unknown;
  disabled?: boolean;
  "aria-checked"?: boolean;
  onClick?: () => void;
  onChange?: (event: { target: { value: string } }) => void;
  onKeyDown?: (event: KeyboardEvent<HTMLButtonElement>) => void;
};

// Capture the rendered elements under React's hook dispatcher, without a DOM dependency.
function renderControl(overrides: Partial<ClinicalFieldControlProps> = {}) {
  const props: ClinicalFieldControlProps = {
    descriptor: { path: "respiratory.wheezing", label: "Wheezing", kind: "boolean", nullable: true, assessments: ["respiratory"] },
    value: null, acceptedValue: null, pending: false, source: "accepted", onChange: vi.fn(),
    ...overrides,
  };
  const elements: ReactElement<ElementProps>[] = [];
  function visit(node: ReactNode) {
    Children.forEach(node, (child) => {
      if (isValidElement<ElementProps>(child)) {
        elements.push(child);
        visit(child.props.children);
      }
    });
  }
  function Capture() {
    const tree = ClinicalFieldControl(props);
    visit(tree);
    return tree;
  }
  const html = renderToStaticMarkup(<Capture />);
  return { html, elements, onChange: props.onChange };
}

describe("ClinicalFieldControl", () => {
  it("preserves canonical inability polarity with the guide's Able/Unable labels", () => {
    const { elements, onChange } = renderControl({ value: false, pending: true, source: "voice", booleanLabels: { yes: "Unable", no: "Able" } });
    const radios = elements.filter((element) => element.props.role === "radio");
    expect(radios.map((radio) => [radio.props.children, radio.props["aria-checked"]])).toEqual([
      ["Unable", false], ["Able", true], ["Not assessed", false],
    ]);
    radios[1].props.onClick?.();
    expect(onChange).toHaveBeenCalledWith(false);
  });
  it("renders a labelled three-way radio group, with unknown distinct from No", () => {
    const { html, elements, onChange } = renderControl();
    const radios = elements.filter((element) => element.props.role === "radio");
    expect(radios.map((radio) => [radio.props.children, radio.props["aria-checked"]])).toEqual([
      ["Yes", false], ["No", false], ["Not assessed", true],
    ]);
    expect(html).toContain('role="radiogroup" aria-labelledby=');
    expect(html).toContain(">Wheezing</label>");
    expect(html).not.toContain('type="checkbox"');
    expect(html).not.toContain("respiratory.wheezing");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("sends booleans and null, including a click on an already selected answer", () => {
    const { elements, onChange } = renderControl({ value: true, acceptedValue: true });
    for (const radio of elements.filter((element) => element.props.role === "radio")) radio.props.onClick?.();
    expect(onChange).toHaveBeenNthCalledWith(1, true);
    expect(onChange).toHaveBeenNthCalledWith(2, false);
    expect(onChange).toHaveBeenNthCalledWith(3, null);
  });

  it.each([["ArrowRight", false, 1], ["ArrowLeft", null, 2], ["Home", true, 0], ["End", null, 2]] as const)(
    "supports explicit radio keyboard selection with %s", (key, value, index) => {
      const { elements, onChange } = renderControl({ value: true });
      const buttons = [0, 1, 2].map(() => ({ focus: vi.fn() }));
      const preventDefault = vi.fn();
      elements.find((element) => element.props.role === "radio")!.props.onKeyDown?.({
        key, preventDefault,
        currentTarget: { parentElement: { querySelectorAll: () => buttons } },
      } as unknown as KeyboardEvent<HTMLButtonElement>);
      expect(preventDefault).toHaveBeenCalledOnce();
      expect(buttons[index].focus).toHaveBeenCalledOnce();
      expect(onChange).toHaveBeenCalledWith(value);
    },
  );

  it("uses unique group labels when the same canonical field appears twice", () => {
    const props: ClinicalFieldControlProps = {
      descriptor: { path: "danger_signs.lethargic_or_unconscious", label: "Lethargic or unconscious", kind: "boolean", nullable: true, assessments: ["danger", "diarrhoea"] },
      value: null, acceptedValue: null, pending: false, source: "accepted", onChange: vi.fn(),
    };
    const html = renderToStaticMarkup(<><ClinicalFieldControl {...props} /><ClinicalFieldControl {...props} /></>);
    const ids = Array.from(html.matchAll(/<label id="([^"]+)"/g), (match) => match[1]);
    expect(ids).toHaveLength(2);
    expect(new Set(ids).size).toBe(2);
    for (const id of ids) expect(html).toContain(`role="radiogroup" aria-labelledby="${id}"`);
  });

  it.each(["", "-", "1.", "12x", "0", "37.5"])("sends raw numeric text %j without coercion", (raw) => {
    const { html, elements, onChange } = renderControl({
      descriptor: { path: "fever.temperature_c", label: "Temperature", kind: "number", nullable: true, unit: "C", assessments: ["fever"] },
      value: 37, raw,
    });
    const input = elements.find((element) => element.type === "input")!;
    expect(input.props.value).toBe(raw);
    expect(html).toContain('type="text" inputMode="decimal"');
    expect(html).not.toContain("Minimum:");
    expect(html).not.toContain("Maximum:");
    input.props.onChange?.({ target: { value: raw } });
    expect(onChange).toHaveBeenCalledWith(raw);
    elements.find((element) => element.type === "button" && element.props.children === "Not assessed")!.props.onClick?.();
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it.each([undefined, null, 0, 12, "12."])("displays numeric value %j when raw is absent", (value) => {
    const { elements, html } = renderControl({
      descriptor: { path: "patient_facts.age_months", label: "Age", kind: "integer", nullable: true, assessments: ["danger"], unit: "months", minimum: 0, maximum: 59 },
      value,
    });
    expect(elements.find((element) => element.type === "input")?.props.value).toBe(value == null ? "" : String(value));
    expect(html).toContain('inputMode="numeric"');
    expect(html).toContain("Minimum: 0. Maximum: 59 (months)");
  });

  it("uses actual enum values with human-readable labels and an explicit unknown choice", () => {
    const { html, elements, onChange } = renderControl({
      descriptor: {
        path: "diarrhoea.dehydration.skin_pinch", label: "Skin pinch", kind: "enum", nullable: true, assessments: ["diarrhoea"],
        options: [{ value: "NORMAL", label: "Normal" }, { value: "VERY_SLOWLY", label: "Very slowly" }],
      },
      acceptedValue: "VERY_SLOWLY", value: "NORMAL", source: "voice", pending: true,
    });
    expect(html).toContain("Confirmed: Very slowly");
    expect(html).not.toContain("VERY_SLOWLY");
    const radios = elements.filter((element) => element.props.role === "radio");
    radios[1].props.onClick?.();
    expect(onChange).toHaveBeenLastCalledWith("VERY_SLOWLY");
    radios[2].props.onClick?.();
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it.each([
    ["voice", "From recording"], ["worker", "Your answer"], ["accepted", "Not assessed"],
    ["kept", "Kept confirmed answer"], ["conflict", "Conflicting recordings"],
  ] as const)("shows a small human-readable badge for %s", (source, label) => {
    expect(renderControl({ source }).html).toContain(`class="clinical-field-control__source">${label}</span>`);
  });

  it("prefills a flagged voice answer without treating its highlight as explicit confirmation", () => {
    const { html, elements, onChange } = renderControl({ value: false, acceptedValue: true, source: "voice", pending: true, requiresChoice: true });
    const no = elements.find((element) => element.props.role === "radio" && element.props.children === "No")!;
    expect(no.props["aria-checked"]).toBe(true);
    expect(html).toContain("Choose an answer to confirm this observation.");
    expect(onChange).not.toHaveBeenCalled();
    no.props.onClick?.();
    expect(onChange).toHaveBeenCalledWith(false);
    expect(renderControl({ acceptedValue: false, value: false }).html).toContain('class="clinical-field-control__source">Confirmed</span>');
  });

  it("requires an explicit choice for a null proposal and keeps rejection separate", () => {
    const onKeep = vi.fn();
    const { html, elements, onChange } = renderControl({ value: null, acceptedValue: false, pending: true, source: "conflict", requiresChoice: true, onKeep });
    expect(html).toContain("Confirmed: No");
    expect(html).toContain("Choose an answer");
    expect(elements.filter((element) => element.props.role === "radio").every((radio) => !radio.props["aria-checked"])).toBe(true);
    expect(onChange).not.toHaveBeenCalled();
    expect(onKeep).not.toHaveBeenCalled();
    elements.find((element) => element.props.children === "Keep confirmed answer")!.props.onClick?.();
    expect(onKeep).toHaveBeenCalledOnce();
    expect(onChange).not.toHaveBeenCalled();
    elements.find((element) => element.props.children === "Not assessed")!.props.onClick?.();
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("shows accepted numeric values with units and associates validation errors", () => {
    const { html } = renderControl({
      descriptor: { path: "respiratory.respiratory_rate", label: "Respiratory rate", kind: "integer", nullable: true, unit: "breaths/min", assessments: ["respiratory"] },
      value: 40, raw: "40x", acceptedValue: 40, pending: true, source: "worker", error: "Enter a whole number.",
    });
    expect(html).toContain("Confirmed: 40 breaths/min");
    expect(html).toContain('aria-invalid="true" aria-describedby=');
    expect(html).toContain('role="alert">Enter a whole number.</p>');
    expect(renderControl({ value: true, acceptedValue: true, pending: true }).html).not.toContain("Confirmed: Yes");
  });

  it.each(["boolean", "integer", "enum"] as const)("disables all %s controls including keep", (kind) => {
    const { elements } = renderControl({
      descriptor: { path: "test", label: "Observation", kind, nullable: true, assessments: ["danger"] },
      disabled: true, onKeep: vi.fn(),
    });
    expect(elements.filter((element) => element.type === "input" || element.type === "button").every((element) => element.props.disabled)).toBe(true);
  });
});
