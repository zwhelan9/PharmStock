import clsx from 'clsx'

const styles = {
  high:    'bg-red-100 text-red-700 border border-red-200',
  medium:  'bg-yellow-100 text-yellow-700 border border-yellow-200',
  low:     'bg-blue-100 text-blue-700 border border-blue-200',
  expired: 'bg-red-100 text-red-800 border border-red-300',
  critical:'bg-orange-100 text-orange-700 border border-orange-200',
  warning: 'bg-yellow-100 text-yellow-700 border border-yellow-200',
  watch:   'bg-blue-100 text-blue-700 border border-blue-200',
  ok:      'bg-green-100 text-green-700 border border-green-200',
}

export default function AlertBadge({ type = 'medium', label }) {
  return (
    <span className={clsx('badge text-xs font-semibold', styles[type] || styles.medium)}>
      {label ?? type}
    </span>
  )
}
