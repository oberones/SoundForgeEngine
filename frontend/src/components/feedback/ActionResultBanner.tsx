import type { MutationFeedback } from "../../services/types";

interface ActionResultBannerProps {
  feedback: MutationFeedback;
}

export function ActionResultBanner({ feedback }: ActionResultBannerProps) {
  if (feedback.state === "idle" || !feedback.message) {
    return null;
  }
  return (
    <div className={`status-banner ${feedback.state}`} role="status">
      <span className="status-pill">action</span>
      <p>{feedback.message}</p>
    </div>
  );
}
