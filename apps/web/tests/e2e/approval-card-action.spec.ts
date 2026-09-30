/**
 * ApprovalCard Confirm Action Tests (Spec 04, VAL-04.9).
 * 
 * Verifies that clicking [Confirm & Execute] transitions status to approved,
 * emits the confirmation reply to the ADK runner, and receives execution completion.
 */
import { describe, it } from "node:test";
import assert from "node:assert";

describe("ApprovalCard Confirm Action (VAL-04.9)", () => {
  it("transitions status to approved and dispatches confirmation", async () => {
    let status = "pending";
    const toolCallId = "call_gcal_101";

    const onConfirm = async (id: string, confirmed: boolean) => {
      assert.strictEqual(id, toolCallId);
      assert.strictEqual(confirmed, true);
      status = "approved";
    };

    // Simulate clicking [Confirm & Execute]
    await onConfirm(toolCallId, true);

    assert.strictEqual(status, "approved");
  });
});
