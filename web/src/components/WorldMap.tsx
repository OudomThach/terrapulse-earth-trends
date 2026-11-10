/** A 3D globe with satellite imagery. Dots are coloured by trend (direction), ringed when significant. */

import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { FeatureCollection, Point } from 'geojson'
import { useEffect, useRef } from 'react'
import type { EventItem, RegionalRow } from '../api/types'
import { signed } from '../lib/format'
import { C, diverging } from '../lib/palette'

const TILES = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg'
const EVENT_COLORS: Record<string, string> = {
  Wildfires: '#ffb347', 'Sea and Lake Ice': '#8fd3ff', 'Severe Storms': C.violet, Volcanoes: '#ff6b6b',
}

interface Props {
  rows: RegionalRow[]
  unit: string
  decimals: number
  satellite: boolean
  selected: string
  events: EventItem[] | null
  onSelect: (name: string) => void
}

/** Value used as the ±limit of the colour scale: the 85th percentile of the absolute rates. */
export function colourLimit(values: number[]): number {
  const a = values.map(Math.abs).sort((x, y) => x - y)
  if (!a.length) return 1
  return Math.max(a[Math.min(a.length - 1, Math.floor(0.85 * a.length))]!, 1e-9)
}

/** MapLibre globe that colours places by trend and opens a place on click. */
export default function WorldMap({ rows, unit, decimals, satellite, selected, events, onSelect }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const ready = useRef(false)
  const latest = useRef({ rows, satellite, selected, events, onSelect })
  latest.current = { rows, satellite, selected, events, onSelect }

  const apply = () => {
    const map = mapRef.current
    if (!map || !ready.current) return
    const { rows: r, satellite: sat, selected: sel, events: ev } = latest.current
    const zmax = colourLimit(r.map((x) => x.perDecade))
    ;(map.getSource('places') as maplibregl.GeoJSONSource).setData({
      type: 'FeatureCollection',
      features: r.map((x) => ({
        type: 'Feature', geometry: { type: 'Point', coordinates: [x.lon, x.lat] },
        properties: { name: x.name, biome: x.biome, perDecade: x.perDecade, p: x.p, significant: x.significant, color: diverging(x.perDecade, zmax) },
      })),
    })
    ;(map.getSource('events') as maplibregl.GeoJSONSource).setData({
      type: 'FeatureCollection',
      features: (ev ?? []).map((e) => ({
        type: 'Feature', geometry: { type: 'Point', coordinates: [e.lon, e.lat] },
        properties: { title: e.title, date: e.date, color: EVENT_COLORS[e.category] ?? C.ink2 },
      })),
    })
    map.setLayoutProperty('sat', 'visibility', sat ? 'visible' : 'none')
    map.setFilter('selected', ['==', ['get', 'name'], sel])
  }

  useEffect(() => {
    const el = host.current
    if (!el) return
    const map = new maplibregl.Map({
      container: el,
      center: [10, 22],
      zoom: 1.35,
      attributionControl: false,
      style: {
        version: 8,
        projection: { type: 'globe' },
        sources: { sat: { type: 'raster', tiles: [TILES], tileSize: 256, maxzoom: 8 } },
        layers: [
          { id: 'bg', type: 'background', paint: { 'background-color': '#10141a' } },
          { id: 'sat', type: 'raster', source: 'sat', paint: { 'raster-opacity': 0.92 } },
        ],
      } as unknown as maplibregl.StyleSpecification,
    })
    mapRef.current = map
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 14 })

    map.on('load', () => {
      const empty = { type: 'FeatureCollection', features: [] } as FeatureCollection
      map.addSource('places', { type: 'geojson', data: empty })
      map.addSource('events', { type: 'geojson', data: empty })
      map.addLayer({ id: 'events', type: 'circle', source: 'events',
        paint: { 'circle-radius': 4, 'circle-color': ['get', 'color'], 'circle-opacity': 0.9, 'circle-stroke-width': 1, 'circle-stroke-color': '#0b0d10' } })
      map.addLayer({ id: 'ring', type: 'circle', source: 'places', filter: ['==', ['get', 'significant'], true],
        paint: { 'circle-radius': 14, 'circle-color': '#f0efec', 'circle-opacity': 0.95 } })
      map.addLayer({ id: 'dots', type: 'circle', source: 'places',
        paint: {
          'circle-radius': ['case', ['get', 'significant'], 10, 7], 'circle-color': ['get', 'color'],
          'circle-opacity': ['case', ['get', 'significant'], 1, 0.62], 'circle-stroke-width': ['case', ['get', 'significant'], 0, 1],
          'circle-stroke-color': '#0b0d10',
        } })
      map.addLayer({ id: 'selected', type: 'circle', source: 'places', filter: ['==', ['get', 'name'], ''],
        paint: { 'circle-radius': 19, 'circle-color': 'rgba(0,0,0,0)', 'circle-stroke-width': 2, 'circle-stroke-color': C.accent } })
      ready.current = true
      apply()
    })

    map.on('mousemove', 'dots', (e) => {
      map.getCanvas().style.cursor = 'pointer'
      const f = e.features?.[0]
      if (!f) return
      const p = f.properties as { name: string; biome: string; perDecade: number; p: number; significant: boolean | string }
      const box = document.createElement('div')
      box.innerHTML = '<b></b><br><span></span><br><small></small>'
      box.querySelector('b')!.textContent = `${p.name} · ${p.biome}`
      box.querySelector('span')!.textContent = `${signed(Number(p.perDecade), decimalsRef.current)} ${unitRef.current} per decade`
      box.querySelector('small')!.textContent = `p = ${Number(p.p).toFixed(3)}${p.significant === true || p.significant === 'true' ? ' (significant)' : ''}`
      popup.setLngLat((f.geometry as Point).coordinates as [number, number]).setDOMContent(box).addTo(map)
    })
    map.on('mouseleave', 'dots', () => {
      map.getCanvas().style.cursor = ''
      popup.remove()
    })
    map.on('click', 'dots', (e) => {
      const name = e.features?.[0]?.properties?.name as string | undefined
      if (name) latest.current.onSelect(name)
    })
    return () => {
      ready.current = false
      map.remove()
      mapRef.current = null
    }
  }, [])

  const unitRef = useRef(unit)
  const decimalsRef = useRef(decimals)
  unitRef.current = unit
  decimalsRef.current = decimals

  useEffect(apply, [rows, satellite, selected, events])

  // fly to the selected place (smooth camera move)
  useEffect(() => {
    const row = rows.find((r) => r.name === selected)
    if (row && mapRef.current) mapRef.current.flyTo({ center: [row.lon, row.lat], zoom: 2.4, speed: 0.7, essential: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected])

  return <div ref={host} style={{ width: '100%', height: '100%' }} aria-label="World map of trends" role="application" />
}
