/**
 * Renders a topic name, stripping the "(H)" suffix and replacing it with a
 * styled inline honors badge. Works in both server and client components.
 */

interface TopicNameProps {
  name: string
  /** Font size of the badge (defaults to 10px) */
  badgeSize?: number
}

export function TopicName({ name, badgeSize = 10 }: TopicNameProps) {
  const isHonors = name.endsWith(' (H)')
  const displayName = isHonors ? name.slice(0, -4) : name

  return (
    <>
      {displayName}
      {isHonors && <HonorsTag size={badgeSize} />}
    </>
  )
}

interface HonorsTagProps {
  size?: number
}

export function HonorsTag({ size = 10 }: HonorsTagProps) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        marginLeft: 7,
        padding: '1px 6px',
        borderRadius: 4,
        fontSize: size,
        fontWeight: 700,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        color: 'var(--adv-color)',
        background: 'var(--adv-dim)',
        border: '1px solid color-mix(in srgb, var(--adv-color) 25%, transparent)',
        verticalAlign: 'middle',
        lineHeight: 1.6,
        fontFamily: 'var(--font-instrument), system-ui, sans-serif',
      }}
    >
      H
    </span>
  )
}

/** Strip " (H)" suffix — for use where only the plain string is needed (e.g. <title>, breadcrumbs). */
export function stripHonors(name: string): string {
  return name.endsWith(' (H)') ? name.slice(0, -4) : name
}
