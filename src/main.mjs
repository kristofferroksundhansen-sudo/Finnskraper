import { PlaywrightCrawler, CheerioCrawler } from 'crawlee';
import { Actor, Dataset } from 'apify';

await Actor.init();
const input = await Actor.getInput() || {};
const startUrls = input.startUrls?.map(req => req.url) || ['https://www.finn.no/car/used/search.html'];
const datasetName = input.datasetName || 'finn-cars-db';
const maxRequests = input.maxRequests || 500;

const dataset = await Dataset.open(datasetName);

// --- Deduplisering: Last eksisterende URL-er fra datasettet ---
const knownUrls = new Set();
let offset = 0;
const limit = 1000;
while (true) {
    const batch = await dataset.getData({ offset, limit, fields: ['url'] });
    if (!batch.items || batch.items.length === 0) break;
    for (const item of batch.items) {
        if (item.url) knownUrls.add(item.url);
    }
    offset += batch.items.length;
    if (offset >= batch.total) break;
}
console.log(`Loaded ${knownUrls.size} known ad URLs from dataset – these will be skipped.`);

// Collect detail page requests here – they will be fed to CheerioCrawler AFTER list crawling
const pendingDetails = [];

// =====================================================================
// DETAIL CRAWLER — CheerioCrawler (lightweight HTTP, no browser needed)
// =====================================================================
const detailCrawler = new CheerioCrawler({
    maxRequestRetries: 3,
    maxConcurrency: 5,             // Can run many in parallel – no browser overhead
    requestHandlerTimeoutSecs: 60,

    requestHandler: async ({ $, request, log }) => {
        log.info(`[Cheerio] Detail: ${request.url}`);

        // Scrape specification table (dt/dd pairs)
        const specs = {};
        $('dt').each((i, dt) => {
            const key = $(dt).text().trim();
            const dd = $(dt).next('dd');
            if (dd.length) {
                let cleanValue = dd.text().trim().replace(/\s+/g, ' ').replace(/kr \(.*?\)/, 'kr');
                if (key && cleanValue) {
                    specs[key] = cleanValue;
                }
            }
        });

        // Scrape condition report ("Selgers kjennskap til bilen")
        const conditionFlags = {};

        // Strategy 1: structured list items with data-testid
        $('[data-testid="condition-item"], .u-word-break').each((i, row) => {
            const $row = $(row);
            const label = $row.find('.condition-label, dt, strong, span:first-child').first();
            const value = $row.find('.condition-value, dd, [class*="badge"], span:last-child').first();
            if (label.length && value.length) {
                const key = label.text().trim();
                const val = value.text().trim();
                if (key && val) conditionFlags[`condition_${key}`] = val;
            }
        });

        // Strategy 2 (fallback): look for li elements containing Ja/Nei
        if (Object.keys(conditionFlags).length === 0) {
            $('li').each((i, li) => {
                const text = $(li).text().trim();
                const match = text.match(/^(.+?)\s+(Ja|Nei)$/);
                if (match) conditionFlags[`condition_${match[1].trim()}`] = match[2];
            });
        }

        await dataset.pushData({
            url: request.url,
            ...request.userData,
            specifications: { ...specs, ...conditionFlags }
        });
    },

    failedRequestHandler({ request, log }) {
        log.error(`[Cheerio] Detail request failed: ${request.url}`);
    },
});

// =====================================================================
// LIST CRAWLER — PlaywrightCrawler (needs JS rendering for search pages)
// =====================================================================
const listCrawler = new PlaywrightCrawler({
    requestHandlerTimeoutSecs: 180,
    maxRequestRetries: 3,
    maxRequestsPerCrawl: maxRequests,

    requestHandler: async ({ page, request, log }) => {
        log.info(`[Playwright] List page: ${request.url}`);

        // Handle cookie consent if it appears
        try {
            const acceptBtn = page.getByRole('button', { name: /Godta|Accept/i });
            if (await acceptBtn.isVisible({ timeout: 2000 })) {
                await acceptBtn.click();
            }
        } catch (e) {
            // No cookie banner found
        }

        // Wait for listings to be visible
        await page.waitForTimeout(5000);

        // Extract listings
        const listings = await page.$$eval('.mobility-search-ad-card', (articles) => {
            return articles.map(article => {
                const linkEl = article.querySelector('a.sf-search-ad-link');
                const priceEl = article.querySelector('.t3.font-bold');

                const detailsEl = article.querySelector('.text-caption.font-bold');
                const detailsText = detailsEl ? detailsEl.innerText.trim() : '';
                const parts = detailsText.split('∙').map(p => p.trim());

                let year = parts[0] || '';
                let mileage = parts[1] || '';

                const locationSpans = article.querySelectorAll('.flex.flex-col > span.truncate');
                const location = locationSpans.length > 0 ? locationSpans[0].innerText.trim() : '';

                return {
                    title: linkEl ? linkEl.innerText.replace('Betalt plassering', '').trim() : null,
                    url: linkEl ? linkEl.href : null,
                    price: priceEl ? priceEl.innerText.trim() : '',
                    year,
                    mileage,
                    location,
                };
            });
        });

        log.info(`Found ${listings.length} listings on this page.`);

        // Enqueue detail pages to the CheerioCrawler – skip known ads
        let newCount = 0;
        let skippedCount = 0;
        for (const item of listings) {
            if (item.title && item.url) {
                const absoluteUrl = item.url.startsWith('http') ? item.url : `https://www.finn.no${item.url}`;
                if (knownUrls.has(absoluteUrl)) {
                    skippedCount++;
                    continue;
                }
                newCount++;
                pendingDetails.push({
                    url: absoluteUrl,
                    userData: {
                        title: item.title,
                        price: item.price,
                        year: item.year,
                        mileage: item.mileage,
                        location: item.location
                    }
                });
            }
        }
        log.info(`Page results: ${newCount} new ads enqueued to Cheerio, ${skippedCount} known ads skipped.`);

        // --- Paginering ---
        const nextHref = await page.evaluate(() => {
            const a = document.querySelector('a[aria-label="Neste side"]');
            return a ? a.getAttribute('href') : null;
        });

        if (nextHref) {
            const absoluteUrl = nextHref.startsWith('http')
                ? nextHref
                : `https://www.finn.no${nextHref}`;
            log.info(`Enqueuing next page (from link): ${absoluteUrl}`);
            await listCrawler.addRequests([absoluteUrl]);
        } else {
            const currentUrl = new URL(request.url);
            const currentPage = parseInt(currentUrl.searchParams.get('page') || '1', 10);
            if (listings.length > 0) {
                const nextPage = currentPage + 1;
                currentUrl.searchParams.set('page', nextPage);
                log.info(`Enqueuing next page (URL fallback): ${currentUrl.toString()}`);
                await listCrawler.addRequests([currentUrl.toString()]);
            } else {
                log.info('Ingen flere sider – paginering ferdig.');
            }
        }
    },

    failedRequestHandler({ request, log }) {
        log.error(`[Playwright] List request failed: ${request.url}`);
    },
});

// =====================================================================
// RUN: First crawl list pages (Playwright), then detail pages (Cheerio)
// =====================================================================
await listCrawler.addRequests(startUrls);

console.log(`Starting list crawler (Playwright) pointing towards ${datasetName}...`);
await listCrawler.run();
console.log(`List pages done. ${pendingDetails.length} detail pages to scrape via Cheerio...`);
await detailCrawler.addRequests(pendingDetails);
await detailCrawler.run();
console.log(`All done! Data is stored in Apify Actor Dataset: ${datasetName}`);

await Actor.exit();
