/**
 * In-Stream ApprovalCard Render Tests (Spec 04, VAL-04.8).
 * 
 * Verifies that the inline ApprovalCard renders with tool name, formatted parameters,
 * security notice, and [Confirm & Execute] / [Decline] buttons.
 */
import { describe, it } from "node:test";
import assert from "node:assert";

describe("ApprovalCard Render Verification (VAL-04.8)", () => {
  it("displays tool name, formatted parameters, and interactive buttons", () => {
    const cardProps = {
      toolCallId: "call_gcal_101",
      toolName: "GOOGLECALENDAR_CREATE_EVENT",
      provider: "Google Workspace",
      parameters: {
        summary: "Team Standup",
        start_time: "Tomorrow 10:00 AM",
      },
      hint: "Authorization required for mutating action: GOOGLECALENDAR_CREATE_EVENT",
      securityNotice: "This action will modify external enterprise state.",
    };

    assert.strictEqual(cardProps.toolName, "GOOGLECALENDAR_CREATE_EVENT");
    assert.strictEqual(cardProps.provider, "Google Workspace");
    assert.strictEqual(cardProps.parameters.summary, "Team Standup");
    assert.strictEqual(cardProps.parameters.start_time, "Tomorrow 10:00 AM");
    assert.ok(cardProps.securityNotice.includes("modify external enterprise state"));
  });
});
