import { isValidElement, type ComponentProps, type FormEvent, type ReactElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PatientIntake } from "./PatientIntake";

// Match the App interaction tests' state scheduler without a DOM dependency.
const hooks = vi.hoisted(() => ({ active: false, cursor: 0, values: [] as unknown[] }));
vi.mock("react", async (importOriginal) => {
  const react = await importOriginal<typeof import("react")>();
  return { ...react, useState(initial: unknown) {
    if (!hooks.active) return react.useState(initial);
    const index = hooks.cursor++;
    if (!(index in hooks.values)) hooks.values[index] = initial;
    return [hooks.values[index], (next: unknown) => {
      hooks.values[index] = typeof next === "function" ? next(hooks.values[index]) : next;
    }];
  } };
});

type Element = ReactElement<Record<string, unknown>>;
function elements(tree: ReactNode): Element[] {
  if (Array.isArray(tree)) return tree.flatMap(elements);
  return isValidElement<Record<string, unknown>>(tree) ? [tree, ...elements(tree.props.children as ReactNode)] : [];
}
let props: ComponentProps<typeof PatientIntake>;
function view() {
  hooks.cursor = 0;
  hooks.active = true;
  try { return PatientIntake(props); } finally { hooks.active = false; }
}
const field = (id: string) => elements(view()).find((node) => node.props.id === id)!;
const button = (label: string) => elements(view()).find((node) => node.type === "button" && node.props.children === label)!;
const edit = (id: string, value: string) => (field(id).props.onChange as (event: { target: { value: string } }) => void)({ target: { value } });
const click = (label: string) => (button(label).props.onClick as () => void)();
function submit() {
  const event = { preventDefault: vi.fn() };
  view().props.onSubmit(event as unknown as FormEvent<HTMLFormElement>);
  expect(event.preventDefault).toHaveBeenCalledOnce();
}

beforeEach(() => {
  hooks.values = [];
  props = { age: null, revision: 7, busy: false, error: "", onSave: vi.fn().mockResolvedValue(false) };
});

describe("PatientIntake", () => {
  it("has required bounded inputs, a local-only privacy notice, and no processing controls", () => {
    expect(field("patient-name").props).toMatchObject({ type: "text", required: true, maxLength: 200, autoComplete: "off", value: "" });
    expect(field("patient-age").props).toMatchObject({ type: "number", required: true, min: 2, max: 59, step: 1, inputMode: "numeric", value: "" });
    const html = renderToStaticMarkup(view());
    expect(html).toContain("The intake name stays in this browser tab");
    expect(html).toContain("not automatically sent for text interpretation");
    expect(html).not.toMatch(/<select|microphone|Intron|Interpret text|Save patient details/);
  });

  it.each([
    ["", "24"], ["   ", "24"], ["x".repeat(201), "24"],
    ["Synthetic Patient", ""], ["Synthetic Patient", " "], ["Synthetic Patient", "1"],
    ["Synthetic Patient", "60"], ["Synthetic Patient", "24.5"], ["Synthetic Patient", "12x"],
    ["Synthetic Patient", "NaN"], ["Synthetic Patient", "Infinity"],
  ])("validates and preserves invalid name=%j age=%j without saving", (name, age) => {
    edit("patient-name", name);
    edit("patient-age", age);
    // Invoke submit directly to verify local validation independently of native constraints.
    submit();
    expect(props.onSave).not.toHaveBeenCalled();
    expect(renderToStaticMarkup(view())).toContain('role="alert">Enter a patient name and age in completed months, from 2 to 59.');
    expect(field("patient-name").props.value).toBe(name);
    expect(field("patient-age").props.value).toBe(age);
    expect(button("Start assessment").props.disabled).toBe(false);
    edit("patient-name", "Synthetic Patient");
    edit("patient-age", "24");
    submit();
    expect(props.onSave).toHaveBeenCalledExactlyOnceWith("Synthetic Patient", 24, 7);
    expect(renderToStaticMarkup(view())).not.toContain('role="alert"');
  });

  it.each([2, 59])("submits a trimmed name and boundary age %s with the original revision", (age) => {
    edit("patient-name", `  ${"x".repeat(200)}  `);
    edit("patient-age", String(age));
    submit();
    expect(props.onSave).toHaveBeenCalledExactlyOnceWith("x".repeat(200), age, 7);
  });

  it("retains both edited fields after a failed save and permits an explicit retry", async () => {
    props = { ...props, patientName: "Original Patient", age: 24, onCancel: vi.fn() };
    edit("patient-name", "Edited Patient");
    edit("patient-age", "36");
    submit();
    await Promise.resolve();
    props = { ...props, error: "Service unavailable. Accepted findings are unchanged." };
    expect(renderToStaticMarkup(view())).toContain('role="alert">Service unavailable. Accepted findings are unchanged.');
    expect(field("patient-name").props.value).toBe("Edited Patient");
    expect(field("patient-age").props.value).toBe("36");
    expect(props.onCancel).not.toHaveBeenCalled();
    expect(button("Save patient details").props.disabled).toBe(false);
    vi.mocked(props.onSave).mockResolvedValueOnce(true);
    submit();
    expect(props.onSave).toHaveBeenNthCalledWith(2, "Edited Patient", 36, 7);
  });

  it("preserves invalid drafts across unrelated renders until explicit stale reload", () => {
    props = { ...props, patientName: "Original Patient", age: 24, onCancel: vi.fn() };
    edit("patient-name", "Unsubmitted Patient");
    edit("patient-age", "24.5");
    submit();
    props = { ...props, patientName: "Current Patient", age: 36, revision: 9 };
    expect(field("patient-name").props.value).toBe("Unsubmitted Patient");
    expect(field("patient-age").props.value).toBe("24.5");
    expect(renderToStaticMarkup(view())).toContain("Patient details or confirmed findings changed");
    expect(button("Save patient details").props.disabled).toBe(true);
    submit();
    expect(props.onSave).not.toHaveBeenCalled();
    click("Reload patient details");
    expect(field("patient-name").props.value).toBe("Current Patient");
    expect(field("patient-age").props.value).toBe("36");
    expect(renderToStaticMarkup(view())).not.toContain('role="alert"');
    expect(renderToStaticMarkup(view())).not.toContain("Reload patient details");
    submit();
    expect(props.onSave).toHaveBeenCalledExactlyOnceWith("Current Patient", 36, 9);
  });

  it("disables fields and all actions while busy and guards the submit handler", () => {
    props = { ...props, patientName: "Synthetic Patient", age: 24, onCancel: vi.fn() };
    view();
    props = { ...props, busy: true, revision: 8 };
    for (const node of elements(view()).filter((node) => node.type === "input" || node.type === "button")) expect(node.props.disabled).toBe(true);
    expect(button("Saving patient details...")).toBeDefined();
    submit();
    expect(props.onSave).not.toHaveBeenCalled();
    props = { ...props, busy: false };
    click("Cancel");
    expect(props.onCancel).toHaveBeenCalledOnce();
    expect(props.onSave).not.toHaveBeenCalled();
  });
});
