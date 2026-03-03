'use client';

import { useEffect, useRef, useState } from 'react';

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
}

interface RadarProps {
    deals: Deal[];
    label: string;
}

declare global {
    interface Window {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        Plotly: any;
    }
}

type ViewMode = 'all' | 'deals' | 'overpriced';

export default function DealRadar({ deals, label }: RadarProps) {
    const plotRef = useRef<HTMLDivElement>(null);
    const [viewMode, setViewMode] = useState<ViewMode>('all');

    const underpriced = deals.filter(d => d.value_difference > 0);
    const overpriced = deals.filter(d => d.value_difference <= 0);

    const displayData = viewMode === 'deals'
        ? underpriced
        : viewMode === 'overpriced'
            ? overpriced
            : deals;

    useEffect(() => {
        if (!plotRef.current) return;
        if (displayData.length === 0) {
            if (window.Plotly) window.Plotly.purge(plotRef.current);
            return;
        }

        const renderPlot = () => {
            const under = displayData.filter(d => d.value_difference > 0);
            const over = displayData.filter(d => d.value_difference <= 0);

            const makeTrace = (
                data: Deal[],
                name: string,
                color: string,
                symbol: string,
                borderColor: string
            ) => ({
                x: data.map(d => d.predicted_value),
                y: data.map(d => d.price_cleaned),
                mode: 'markers',
                type: 'scatter',
                name,
                marker: {
                    color,
                    size: 10,
                    symbol,
                    opacity: 0.85,
                    line: { width: 1.5, color: borderColor },
                },
                text: data.map(d => {
                    const diff = d.value_difference;
                    const sign = diff > 0 ? '+' : '';
                    const color = diff > 0 ? '#22c55e' : '#ff6b6b';
                    const label = diff > 0 ? '✅ Under markedsverdi' : '⚠️ Over markedsverdi';
                    return (
                        `<b>${d.title} ${d.year_cleaned ? `(${d.year_cleaned})` : ''}</b><br>` +
                        `${(d.mileage_cleaned ?? 0).toLocaleString('no')} km${d.trim_level && d.trim_level !== 'Ukjent' ? ` · ${d.trim_level}` : ''}<br>` +
                        `Listepris: <b>${(d.price_cleaned ?? 0).toLocaleString('no')} kr</b><br>` +
                        `Markedsverdi: <b>${(d.predicted_value ?? 0).toLocaleString('no')} kr</b><br>` +
                        `<span style="color:${color}">${label}: ${sign}${diff.toLocaleString('no')} kr</span><br>` +
                        `${d.region ?? ''} · ${d.is_dealer ? d.dealer_name || 'Forhandler' : 'Privat'}`
                    );
                }),
                hovertemplate: '%{text}<extra></extra>',
                customdata: data.map(d => d.url),
            });

            const allPrices = [
                ...displayData.map(d => d.price_cleaned),
                ...displayData.map(d => d.predicted_value),
            ].filter(Boolean);
            const minVal = Math.min(...allPrices) * 0.9;
            const maxVal = Math.max(...allPrices) * 1.1;

            const diag = {
                x: [minVal, maxVal],
                y: [minVal, maxVal],
                mode: 'lines',
                type: 'scatter',
                name: 'Rettferdig pris',
                line: { dash: 'dot', color: 'rgba(255,255,255,0.25)', width: 2 },
                hoverinfo: 'skip',
            };

            const traces = [
                diag,
                ...(under.length > 0 ? [makeTrace(under, `✅ Under markedsverdi (${under.length})`, 'rgba(34,197,94,0.8)', 'circle', '#16a34a')] : []),
                ...(over.length > 0 ? [makeTrace(over, `⚠️ Over markedsverdi (${over.length})`, 'rgba(255,107,107,0.75)', 'square', '#dc2626')] : []),
            ];

            const layout = {
                paper_bgcolor: 'transparent',
                plot_bgcolor: 'transparent',
                font: { family: 'Inter, sans-serif', color: '#e2e8f0', size: 12 },
                xaxis: {
                    title: 'Forventet markedsverdi (kr)',
                    gridcolor: 'rgba(255,255,255,0.06)',
                    zerolinecolor: 'rgba(255,255,255,0.1)',
                    tickformat: ',.0f',
                },
                yaxis: {
                    title: 'Listepris på Finn (kr)',
                    gridcolor: 'rgba(255,255,255,0.06)',
                    zerolinecolor: 'rgba(255,255,255,0.1)',
                    tickformat: ',.0f',
                },
                legend: {
                    bgcolor: 'rgba(26,29,46,0.9)',
                    bordercolor: '#2e3250',
                    borderwidth: 1,
                    x: 0.01,
                    y: 0.99,
                },
                margin: { l: 80, r: 20, t: 20, b: 80 },
                shapes: [
                    // Green area = below diagonal = cheap
                    {
                        type: 'path',
                        path: `M ${minVal},${minVal} L ${maxVal},${minVal} L ${maxVal},${maxVal} Z`,
                        fillcolor: 'rgba(34,197,94,0.05)',
                        line: { width: 0 },
                        layer: 'below',
                    },
                    // Red area = above diagonal = expensive
                    {
                        type: 'path',
                        path: `M ${minVal},${minVal} L ${minVal},${maxVal} L ${maxVal},${maxVal} Z`,
                        fillcolor: 'rgba(255,107,107,0.05)',
                        line: { width: 0 },
                        layer: 'below',
                    },
                ],
                annotations: [
                    {
                        x: maxVal * 0.75,
                        y: minVal * 1.05,
                        text: '✅ Billig',
                        showarrow: false,
                        font: { color: 'rgba(34,197,94,0.4)', size: 12 },
                        xanchor: 'center',
                    },
                    {
                        x: minVal * 1.05,
                        y: maxVal * 0.95,
                        text: '⚠️ Dyrt',
                        showarrow: false,
                        font: { color: 'rgba(255,107,107,0.4)', size: 12 },
                        xanchor: 'left',
                    },
                ],
            };

            const config = { displayModeBar: false, responsive: true };

            window.Plotly.react(plotRef.current, traces, layout, config);

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (plotRef.current as any).on('plotly_click', (data: { points: Array<{ customdata: string }> }) => {
                const url = data.points[0]?.customdata;
                if (url) window.open(url, '_blank');
            });
        };

        if (window.Plotly) {
            renderPlot();
        } else {
            const script = document.createElement('script');
            script.src = 'https://cdn.plot.ly/plotly-2.35.2.min.js';
            script.onload = renderPlot;
            document.head.appendChild(script);
        }
    }, [displayData, label]);

    return (
        <div>
            {/* View mode toggle */}
            <div style={{
                display: 'inline-flex',
                background: 'var(--surface-2)',
                border: '1px solid var(--border)',
                borderRadius: 10,
                padding: 4,
                gap: 4,
                marginBottom: 20,
            }}>
                {([
                    { key: 'all', label: `Alle (${deals.length})`, dot: '#a5a0ff' },
                    { key: 'deals', label: `✅ Kupper (${underpriced.length})`, dot: '#22c55e' },
                    { key: 'overpriced', label: `⚠️ Overpriset (${overpriced.length})`, dot: '#ff6b6b' },
                ] as const).map(tab => (
                    <button
                        key={tab.key}
                        onClick={() => setViewMode(tab.key)}
                        style={{
                            padding: '7px 16px',
                            borderRadius: 7,
                            border: 'none',
                            cursor: 'pointer',
                            fontFamily: 'Inter, sans-serif',
                            fontSize: 13,
                            fontWeight: 600,
                            transition: 'all 0.15s',
                            background: viewMode === tab.key
                                ? tab.key === 'deals' ? 'rgba(34,197,94,0.15)'
                                    : tab.key === 'overpriced' ? 'rgba(255,107,107,0.15)'
                                        : 'rgba(108,99,255,0.2)'
                                : 'transparent',
                            color: viewMode === tab.key
                                ? tab.key === 'deals' ? '#22c55e'
                                    : tab.key === 'overpriced' ? '#ff6b6b'
                                        : '#a5a0ff'
                                : 'var(--text-muted)',
                            outline: viewMode === tab.key
                                ? `1px solid ${tab.key === 'deals' ? 'rgba(34,197,94,0.4)' : tab.key === 'overpriced' ? 'rgba(255,107,107,0.4)' : 'rgba(108,99,255,0.4)'}`
                                : 'none',
                        }}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Legend strip */}
            <div style={{ display: 'flex', gap: 20, marginBottom: 12, fontSize: 12, color: 'var(--text-muted)', alignItems: 'center' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#22c55e', display: 'inline-block' }} />
                    Billigpriced (bra kjøp)
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 2, background: '#ff6b6b', display: 'inline-block' }} />
                    Overpriset (unngå)
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 4, borderLeft: '1px solid var(--border)', paddingLeft: 16 }}>
                    🖱️ Klikk på en prikk → åpner Finn-annonsen
                </span>
            </div>

            {displayData.length === 0 ? (
                <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                    Ingen annonser i denne kategorien matcher filtrene dine.
                </div>
            ) : (
                <div ref={plotRef} style={{ width: '100%', height: '480px', cursor: 'crosshair' }} />
            )}
        </div>
    );
}
