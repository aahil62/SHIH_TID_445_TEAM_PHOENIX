import type { ReactElement } from "react";

/** Small distinguishing glyphs per real agent_name — purely decorative
 * (shape/identity only), never a stand-in for the agent's real score or
 * reasons text, which still comes from the API everywhere these are used. */
function RuleIcon() {
  return (
    <path
      d="M4 4h10l4 4v10H4V4Z M14 4v4h4 M8 12h6 M8 15h6"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinejoin="round"
      fill="none"
    />
  );
}

function VelocityIcon() {
  return (
    <>
      <circle cx="11" cy="12" r="8" stroke="currentColor" strokeWidth="1.4" fill="none" />
      <path d="M11 12 15 8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="11" cy="12" r="1.1" fill="currentColor" />
    </>
  );
}

function GraphIcon() {
  return (
    <>
      <circle cx="6" cy="6" r="2" stroke="currentColor" strokeWidth="1.3" fill="none" />
      <circle cx="17" cy="6" r="2" stroke="currentColor" strokeWidth="1.3" fill="none" />
      <circle cx="11" cy="17" r="2" stroke="currentColor" strokeWidth="1.3" fill="none" />
      <path d="M7.6 7.1 15.4 7.1 M7 7.8 10 15.4 M15 7.8 12 15.4" stroke="currentColor" strokeWidth="1.1" />
    </>
  );
}

function BehavioralIcon() {
  return (
    <>
      <circle cx="11" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.4" fill="none" />
      <path d="M4.5 19c0-4 3-6.5 6.5-6.5S17.5 15 17.5 19" stroke="currentColor" strokeWidth="1.4" fill="none" strokeLinecap="round" />
    </>
  );
}

function MlIcon() {
  return (
    <>
      <rect x="6" y="6" width="10" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.4" fill="none" />
      <path
        d="M11 3v3 M11 18v3 M3 11h3 M18 11h3 M5.5 5.5 7.6 7.6 M16.4 16.4 18.5 18.5 M5.5 16.5 7.6 14.4 M16.4 5.6 18.5 3.5"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </>
  );
}

function FraudDnaIcon() {
  return (
    <path
      d="M7 3c0 4 8 4 8 8s-8 4-8 8 M15 3c0 4-8 4-8 8s8 4 8 8 M7.5 7h7 M6.5 15h9"
      stroke="currentColor"
      strokeWidth="1.3"
      fill="none"
      strokeLinecap="round"
    />
  );
}

function GenericIcon() {
  return <circle cx="11" cy="11" r="6" stroke="currentColor" strokeWidth="1.4" fill="none" />;
}

const AGENT_ICON: Record<string, () => ReactElement> = {
  rule_agent: RuleIcon,
  velocity_agent: VelocityIcon,
  graph_agent: GraphIcon,
  behavioral_agent: BehavioralIcon,
  ml_agent: MlIcon,
  fraud_dna_agent: FraudDnaIcon,
};

export function AgentIcon({ agentName, className }: { agentName: string; className?: string }) {
  const Glyph = AGENT_ICON[agentName] ?? GenericIcon;
  return (
    <svg viewBox="0 0 22 22" className={className} aria-hidden="true">
      <Glyph />
    </svg>
  );
}
