import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { ProfileDrawer } from "./ProfileDrawer";
import { DEFAULT_VISA_PROFILE } from "@/visaProfile";

function renderDrawer(open: boolean, onClose = vi.fn()) {
  render(
    <ProfileDrawer
      open={open}
      onClose={onClose}
      profile={DEFAULT_VISA_PROFILE}
      onProfileChange={() => {}}
      onProfileReset={() => {}}
      tracking={{}}
      onImport={() => {}}
    />
  );
  return onClose;
}

describe("ProfileDrawer", () => {
  it("renders nothing when closed", () => {
    renderDrawer(false);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("renders a modal dialog hosting the visa profile when open", () => {
    renderDrawer(true);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("Your visa situation")).toBeInTheDocument();
  });

  it("closes on Escape", () => {
    const onClose = renderDrawer(true);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("closes on backdrop click", () => {
    const onClose = renderDrawer(true);
    fireEvent.click(screen.getByLabelText("Close settings"));
    expect(onClose).toHaveBeenCalled();
  });
});
