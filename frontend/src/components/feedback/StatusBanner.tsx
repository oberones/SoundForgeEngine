import type { MutationFeedback } from "../../services/types";

interface StatusBannerProps {
  feedback: MutationFeedback;
}

export function StatusBanner({ feedback }: StatusBannerProps) {
  if (feedback.state === "idle" || !feedback.message) {
    return null;
  }

  return (
    <div className={`status-banner ${feedback.state}`} role="status">
      <span className="status-pill">{feedback.state}</span>
      <p>{feedback.message}</p>
    </div>
  );
}
