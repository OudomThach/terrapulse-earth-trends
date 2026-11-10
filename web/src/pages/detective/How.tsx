/** Stage 5: the method in five steps, a glossary, the variable dictionary and the honest limits. */

import { Card, DataTable, Section } from '../../components/ui'
import { useMeta } from '../../meta'

const STEPS: [string, string, string][] = [
  ['STEP 1', 'Pick the clues', '20 vital signs of the Earth system: temperature, water, land, sunlight and air.'],
  ['STEP 2', 'Get the record', 'Monthly values from 1990 to 2025 at your chosen spot, from satellite-driven reanalysis.'],
  ['STEP 3', 'Average whole years', 'Yearly averages cancel the seasons, so winter and summer cannot fake a trend.'],
  ['STEP 4', 'Test the trend', "Mann-Kendall test for a rise or fall, Sen's slope for the rate, and a 95% confidence range."],
  ['STEP 5', 'Be sceptical', 'Corrections for testing many variables, for year-to-year memory, and a check for sudden jumps.'],
]

const GLOSSARY: [string, string][] = [
  ['Trend', 'A steady tendency to rise or fall over many years, as opposed to ordinary ups and downs.'],
  ['Significant', 'Unlikely to be luck. We use p < 0.05: if nothing were changing, a pattern this strong would appear less than 5 times in 100.'],
  ['p-value', 'The chance of seeing a pattern at least this strong if there were no real trend. Small means convincing.'],
  ['Mann-Kendall test', 'Compares every pair of years and counts how often the later one is higher. Needs no bell-shaped assumption and is not thrown off by outliers.'],
  ["Sen's slope", 'The median of the slopes between every pair of years: the rate of change, resistant to outliers.'],
  ['Confidence range (95%)', "The span of rates that fit the data. If it includes zero, 'no change' remains plausible."],
  ['Anomaly', 'A value minus the long-term average for that calendar month: how unusual it is for the season.'],
  ['False-discovery correction', 'Test 20 things and one will look significant by chance. Benjamini-Hochberg adjusts the p-values to account for that.'],
  ['Autocorrelation', "A wet year tends to be followed by another wet year. Strong 'memory' makes trends look more convincing than they are, so we adjust."],
  ['Step change', 'A sudden jump instead of a steady slope, often caused by a change in instruments or data processing rather than climate.'],
  ['Reanalysis', 'A weather model constantly corrected with satellite and ground observations to give a complete, consistent record.'],
]

const LIMITS = [
  ['A trend says what, not why.', 'Linking a trend to a cause takes more evidence than one statistic.'],
  ['Each data cell is roughly 50 km wide.', 'Results describe a region, not one street or city.'],
  ['Reanalysis blends model and observations.', 'Changes in the observing system can create artificial jumps, which is why the detective flags abrupt steps (the Greenland cloud case is a real example).'],
  ['36 years is short for slow climate signals.', 'Natural cycles such as El Niño can masquerade as trends over a few decades.'],
  ['Linear trends only.', 'A curved or reversing change is summarised by one straight line.'],
]

/** How-it-works stage: the methods explained in plain language, with a glossary. */
export function How() {
  const { meta } = useMeta()
  return (
    <div className="fade-in">
      <Section title="How the detective works" sub="Five steps, all classic statistics you can check yourself." />
      <div className="how">
        {STEPS.map(([n, h, p]) => <Card key={n}><div className="n">{n}</div><h4>{h}</h4><p>{p}</p></Card>)}
      </div>
      <Section title="Glossary" />
      {GLOSSARY.map(([term, text]) => <details key={term}><summary>{term}</summary><div>{text}</div></details>)}
      <Section title="The variables" />
      <DataTable columns={['Variable', 'Type', 'Unit', 'What it is', 'Record starts']}
        rows={meta.variables.map((v) => [v.name, v.group, v.unit, v.definition, v.since ?? meta.years.first])} />
      <Section title="Honest limits" />
      <Card>
        <div className="stack">{LIMITS.map(([b, t]) => <p key={b}><b>{b}</b> {t}</p>)}</div>
      </Card>
    </div>
  )
}
