/** Reusable display for a masked identifier (account/device/IP labels
 * matching the "ACC-••0110" style).
 *
 * This is deliberately a pass-through formatter, not masking logic: the
 * backend already masks every identifier before it ever reaches the
 * frontend (fraudlens/core/privacy.py's mask_identifier/mask_ip, applied
 * server-side to every response the API sends) — there is no raw value
 * for the client to mask. This component exists so every place an
 * identifier is displayed uses the same consistent styling, not so it
 * can perform masking itself. Never pass an unmasked value into it.
 */
export default function MaskedId({
  value,
  className = "",
}: {
  value: string;
  className?: string;
}) {
  return <span className={`font-mono ${className}`}>{value}</span>;
}
