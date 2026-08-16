export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3 text-red-500">
      <span className="text-4xl">⚠️</span>
      <p className="text-sm font-medium">{message || 'Something went wrong'}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary text-sm mt-1">
          Try again
        </button>
      )}
    </div>
  )
}
