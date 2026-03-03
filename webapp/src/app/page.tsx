'use client';

import { useState, useEffect, useMemo } from 'react';
import dynamic from 'next/dynamic';

const DealRadar = dynamic(() => import('@/components/DealRadar'), { ssr: false });

interface Deal {
  title: string;
  price_cleaned: number;
  predicted_value: number;
  value_difference: number;
  year_cleaned: number;
  mileage_cleaned: number;
  trim_level?: string;
  region?: string;
  is_dealer?: number;
  dealer_name?: string;
  days_listed?: number;
  url?: string;
  car_make?: string;
  car_model?: string;
}

interface Profile { profile: string; label: string; count: number; }

export default function Home() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [activeProfile, setActiveProfile] = useState<string>('');
  const [deals, setDeals] = useState<Deal[]>([]);
  const [label, setLabel] = useState('');

  // Filters
  const [minDiscount, setMinDiscount] = useState(0);
  const [maxKm, setMaxKm] = useState(250000);
  const [minYear, setMinYear] = useState(2015);
  const [sellerType, setSellerType] = useState<'all' | 'private' | 'dealer'>('all');
  const [selectedRegion, setSelectedRegion] = useState('all');
  const [selectedTrim, setSelectedTrim] = useState('all');

  useEffect(() => {
    fetch('/data/index.json')
      .then(r => r.json())
      .then(d => {
        setProfiles(d.profiles);
        if (d.profiles.length > 0) setActiveProfile(d.profiles[0].profile);
      });
  }, []);

  useEffect(() => {
    if (!activeProfile) return;
    fetch(`/data/${activeProfile}.json`)
      .then(r => r.json())
      .then(d => {
        setDeals(d.deals);
        setLabel(d.label);
        setSelectedRegion('all');
        setSelectedTrim('all');
      });
  }, [activeProfile]);

  const regions = useMemo(() => ['all', ...Array.from(new Set(deals.map(d => d.region).filter(Boolean)))], [deals]);
  const trims = useMemo(() => ['all', ...Array.from(new Set(deals.map(d => d.trim_level).filter(Boolean)))], [deals]);

  // radarDeals: all listings matching km/year/region/trim/seller – NO minDiscount filter
  // so the scatter shows the full market (both under and over-priced)
  const radarDeals = useMemo(() => deals.filter(d => {
    if (d.mileage_cleaned > maxKm) return false;
    if (d.year_cleaned < minYear) return false;
    if (sellerType === 'private' && d.is_dealer === 1) return false;
    if (sellerType === 'dealer' && d.is_dealer !== 1) return false;
    if (selectedRegion !== 'all' && d.region !== selectedRegion) return false;
    if (selectedTrim !== 'all' && d.trim_level !== selectedTrim) return false;
    return true;
  }), [deals, maxKm, minYear, sellerType, selectedRegion, selectedTrim]);

  // filtered: applies minDiscount too – used for stats cards + top 10 table
  const filtered = useMemo(() =>
    radarDeals.filter(d => d.value_difference >= minDiscount),
    [radarDeals, minDiscount]);

  const top10 = useMemo(() =>
    [...filtered]
      .filter(d => d.value_difference > 0)
      .sort((a, b) => b.value_difference - a.value_difference)
      .slice(0, 10),
    [filtered]);

  const goodDeals = filtered.filter(d => d.value_difference > 0);
  const avgDiscount = goodDeals.length > 0 ? Math.round(goodDeals.reduce((s, d) => s + d.value_difference, 0) / goodDeals.length) : 0;
  const bestDeal = goodDeals.length > 0 ? Math.max(...goodDeals.map(d => d.value_difference)) : 0;

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      {/* Hero */}
      <div className="gradient-hero" style={{ padding: '48px 32px 32px' }}>
        <div style={{ maxWidth: 1200, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
            <span style={{ fontSize: 28 }}>🚗</span>
            <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.5px' }}>
              Finn Bil-Analyse
            </h1>
            <span className="badge badge-purple">Beta</span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: 15, maxWidth: 540, lineHeight: 1.6 }}>
            Maskinlæring som analyserer bruktbilmarkedet på Finn.no i sanntid – og finner biler som er priset langt under markedsverdi.
          </p>

          {/* Model tabs */}
          <div style={{ display: 'flex', gap: 8, marginTop: 24, flexWrap: 'wrap' }}>
            {profiles.map(p => (
              <button
                key={p.profile}
                className={`nav-tab ${activeProfile === p.profile ? 'active' : ''}`}
                onClick={() => setActiveProfile(p.profile)}
              >
                {p.label}
                <span style={{ marginLeft: 6, fontSize: 11, opacity: 0.6 }}>{p.count}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ maxWidth: 1200, margin: '32px auto', padding: '0 32px' }}>
        {/* Stats row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
          {[
            { num: radarDeals.length, label: 'Annonser analysert' },
            { num: `+${avgDiscount.toLocaleString('no')} kr`, label: 'Snitt-rabatt (deals)' },
            { num: `+${bestDeal.toLocaleString('no')} kr`, label: 'Beste deal nå' },
          ].map((s, i) => (
            <div key={i} className="card stat-block">
              <div className="stat-number">{s.num}</div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Filter bar */}
        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                Min. rabatt (tabell) — {minDiscount.toLocaleString('no')} kr
              </label>
              <input type="range" min={0} max={100000} step={5000} value={minDiscount}
                onChange={e => setMinDiscount(+e.target.value)} style={{ width: 160 }} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
                Maks km — {maxKm.toLocaleString('no')}
              </label>
              <input type="range" min={10000} max={400000} step={10000} value={maxKm}
                onChange={e => setMaxKm(+e.target.value)} style={{ width: 160 }} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Fra årsmodell</label>
              <select value={minYear} onChange={e => setMinYear(+e.target.value)}>
                {[2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024].map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Selger</label>
              <select value={sellerType} onChange={e => setSellerType(e.target.value as 'all' | 'private' | 'dealer')}>
                <option value="all">Alle</option>
                <option value="private">Kun privat</option>
                <option value="dealer">Kun forhandler</option>
              </select>
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Region</label>
              <select value={selectedRegion} onChange={e => setSelectedRegion(e.target.value)}>
                {regions.map(r => <option key={r} value={r}>{r === 'all' ? 'Alle regioner' : r}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Utstyrsn.</label>
              <select value={selectedTrim} onChange={e => setSelectedTrim(e.target.value)}>
                {trims.map(t => <option key={t} value={t}>{t === 'all' ? 'Alle' : t}</option>)}
              </select>
            </div>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ marginBottom: 4 }}>
            <h2 style={{ fontSize: 17, fontWeight: 700 }}>📡 Kupp-Radar – {label}</h2>
            <p className="text-muted" style={{ marginTop: 4, fontSize: 13 }}>
              <span style={{ color: '#22c55e', fontWeight: 600 }}>{radarDeals.filter(d => d.value_difference > 0).length} under markedsverdi</span>
              {' · '}
              <span style={{ color: '#ff6b6b', fontWeight: 600 }}>{radarDeals.filter(d => d.value_difference <= 0).length} over markedsverdi</span>
            </p>
          </div>
          <DealRadar deals={radarDeals} label={label} />
        </div>

        {/* Top 10 table */}
        <div className="card">
          <h2 style={{ fontSize: 17, fontWeight: 700, marginBottom: 20 }}>🏆 Topp 10 Beste Kjøp</h2>
          {top10.length === 0 ? (
            <p className="text-muted" style={{ textAlign: 'center', padding: '32px 0' }}>Ingen annonser matcher valgte filtre.</p>
          ) : top10.map((d, i) => (
            <div key={i} className="deal-row">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent)', minWidth: 22 }}>#{i + 1}</span>
                  <span style={{ fontWeight: 600, fontSize: 15 }}>{d.title} {d.year_cleaned ? `(${d.year_cleaned})` : ''}</span>
                  {d.trim_level && d.trim_level !== 'Ukjent' && <span className="badge badge-purple">{d.trim_level}</span>}
                  {d.is_dealer === 1 ? <span className="badge badge-orange">Forhandler</span> : <span className="badge badge-green">Privat</span>}
                </div>
                <div className="text-muted" style={{ display: 'flex', gap: 16, paddingLeft: 32 }}>
                  <span>🛣️ {d.mileage_cleaned?.toLocaleString('no')} km</span>
                  <span>📍 {d.region || 'Ukjent'}</span>
                  {d.days_listed ? <span>📅 {d.days_listed} dager på Finn</span> : null}
                  {d.dealer_name ? <span>{d.dealer_name}</span> : null}
                </div>
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div className="price-tag">{d.price_cleaned?.toLocaleString('no')} kr</div>
                <div className="text-muted" style={{ marginTop: 2 }}>Markedsverdi: {d.predicted_value?.toLocaleString('no')} kr</div>
                <div className="discount" style={{ marginTop: 4 }}>+{d.value_difference?.toLocaleString('no')} kr rabatt</div>
                {d.url && (
                  <a href={d.url} target="_blank" rel="noopener noreferrer" className="finn-link" style={{ marginTop: 8 }}>
                    Se på Finn ↗
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)', fontSize: 12 }}>
          Data oppdateres daglig fra Finn.no · Prisestimater er basert på maskinlæringsmodell og er veiledende · Gjør alltid ditt eget due diligence
        </div>
      </div>
    </div>
  );
}
