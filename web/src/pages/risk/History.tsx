/** Risk Lab > History: what was saved to the SQLite database. */

import { api } from '../../api/endpoints'
import { Banner, DataTable, ErrorBox, Section, Skeleton } from '../../components/ui'
import { useAsync } from '../../hooks'
import { fixed } from '../../lib/format'

/** Saved runs and forecast comparisons read from the SQLite history. */
export function History() {
  const { data, error } = useAsync(() => api.history(), [])
  if (error) return <ErrorBox error={error} />
  if (!data) return <Skeleton height={240} />
  return (
    <div className="fade-in">
      <Section title="Saved simulation runs" sub="Stored in SQLite. Use 'Save this run' in the fire simulator." />
      {data.simulations.length === 0
        ? <Banner headline="Nothing saved yet" tone="none">Run a fire simulation and press "Save this run".</Banner>
        : <DataTable columns={['#', 'When', 'Region', 'Dryness source', 'Wetness', 'Dryness', 'Wind m/s', 'Toward°', 'Hours', 'Det. ha', 'MC ha', 'IoU']}
            rows={data.simulations.map((s) => [s.id, s.created_at.replace('T', ' '), s.region, s.forecast_model, fixed(s.forecast_wetness, 3), fixed(s.dryness, 2),
              fixed(s.wind_speed_ms, 1), fixed(s.wind_toward_deg, 0), fixed(s.hours, 2), fixed(s.det_burned_ha, 1), fixed(s.prob_burned_ha, 1), fixed(s.iou, 2)])} />}
      <Section title="Saved forecast comparisons" />
      {data.benchmarks.length === 0
        ? <Banner headline="Nothing saved yet" tone="none">Open the Forecast tab and press "Save comparison to history".</Banner>
        : <DataTable columns={['#', 'When', 'Region', 'Horizon', 'Model', 'MSE', 'RMSE', 'R²']}
            rows={data.benchmarks.map((b) => [b.id, b.created_at.replace('T', ' '), b.region, `${b.horizon_days} d`, b.model, b.mse.toFixed(5), b.rmse.toFixed(4), fixed(b.r2, 3)])} />}
    </div>
  )
}
