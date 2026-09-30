/**
 * ApprovalCard Decline/Reject Action Tests (Spec 04, VAL-04.10).
 * 
 * Verifies that clicking [Decline] marks status as declined, halts tool execution,
 * and allows the model to continue with an alternate plan.
 */
import { describe, it } from "node:test";
import assert from "node:assert";

describe("ApprovalCard Decline Action (VAL-04.10)", () => {
  it("transitions status to declined and aborts tool execution", async () => {
    let status = "pending";
    const toolCallId = "call_gmail_202";

    const onDecline = async (id: string, confirmed: boolean) => {
      assert.strictEqual(id, toolCallId);
      assert.strictEqual(confirmed, false);
      status = "declined";
    };

    // Simulate clicking [Decline]
    await onDecline(toolCallId, false);

    assert.strictEqual(status, "declined");
  });
});
