import { StatusBanner } from "../../components/feedback/StatusBanner";
import type { MutationFeedback } from "../../services/types";

interface ControlMutationStateProps {
  feedback: MutationFeedback;
}

export function ControlMutationState({ feedback }: ControlMutationStateProps) {
  return <StatusBanner feedback={feedback} />;
}
