import { useState } from 'react'
import Predictions from './Predictions'
import ReorderRecommendations from './ReorderRecommendations'

const TABS = [
  ['reorder', '🛒 Reorder & Risk'],
  ['forecast', '📈 Demand Forecasts'],
]

export default function ForecastingReorder() {
  const [tab, setTab] = useState('reorder')

  return (
    <div className="space-y-4">
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {TABS.map(([t, l]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === t ? 'bg-white shadow text-blue-700' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      {tab === 'reorder' && <ReorderRecommendations />}
      {tab === 'forecast' && <Predictions />}
    </div>
  )
}
