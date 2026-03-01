import { PlaywrightCrawler } from 'crawlee';
import { Actor, Dataset } from 'apify';

await Actor.init();
const input = await Actor.getInput() || {};
const startUrls = input.startUrls?.map(req => req.url) || ['https://www.finn.no/car/used/search.html'];
const datasetName = input.datasetName || 'finn-cars-db';

const dataset = await Dataset.open(datasetName);

const crawler = new PlaywrightCrawler({
    // Increase timeouts so Apify doesn't kill it as easily
    requestHandlerTimeoutSecs: 180,
    maxRequestRetries: 3,
    maxRequestsPerCrawl: 500, // User requested a safe limit of 100-500 per run

    // Function called for each URL
    requestHandler: async ({ page, request, log }) => {
        log.info(`Processing ${request.url}...`);

        // Handle cookie consent if it appears
        try {
            const acceptBtn = page.getByRole('button', { name: /Godta|Accept/i });
            if (await acceptBtn.isVisible({ timeout: 2000 })) {
                await acceptBtn.click();
            }
        } catch (e) {
            // No cookie banner found
        }

        if (request.label === 'DETAIL') {
            await page.waitForTimeout(2000); // 2 seconds to let things load

            const specs = await page.$$eval('dt', (dts) => {
                const specData = {};
                for (const dt of dts) {
                    const key = dt.textContent;
                    const dd = dt.nextElementSibling;
                    if (dd && dd.tagName.toLowerCase() === 'dd') {
                        const value = dd.textContent;
                        if (key && value) {
                            let cleanValue = value.trim().replace(/\s+/g, ' ').replace(/kr \(.*?\)/, 'kr');
                            specData[key.trim()] = cleanValue;
                        }
                    }
                }
                return specData;
            });

            await dataset.pushData({
                url: request.url,
                ...request.userData,
                specifications: specs
            });
            return;
        }

        // Wait for listings to be visible (or just wait a bit)
        await page.waitForTimeout(5000); // 5 seconds to let things load

        // Extract listings
        const listings = await page.$$eval('.mobility-search-ad-card', (articles) => {
            return articles.map(article => {
                const linkEl = article.querySelector('a.sf-search-ad-link');
                const priceEl = article.querySelector('.t3.font-bold');

                // Details contains format like "2016 ∙ 110&nbsp;682 km ∙ El ∙ 250 km rekkevidde"
                const detailsEl = article.querySelector('.text-caption.font-bold');
                const detailsText = detailsEl ? detailsEl.innerText.trim() : '';
                const parts = detailsText.split('∙').map(p => p.trim());

                let year = parts[0] || '';
                let mileage = parts[1] || '';

                // Location is typically the first span inside the flex-col
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

        // Enqueue detail pages instead of immediately pushing data
        for (const item of listings) {
            if (item.title && item.url) {
                const absoluteUrl = item.url.startsWith('http') ? item.url : `https://www.finn.no${item.url}`;
                await crawler.addRequests([{
                    url: absoluteUrl,
                    label: 'DETAIL',
                    userData: {
                        title: item.title,
                        price: item.price,
                        year: item.year,
                        mileage: item.mileage,
                        location: item.location
                    }
                }]);
            }
        }

        // Find the "Next" page link and enqueue it
        const nextButton = await page.$('a.button--icon-right:has-text("Neste"), a[aria-label="Neste side"]');
        if (nextButton) {
            const nextUrl = await nextButton.getAttribute('href');
            if (nextUrl) {
                log.info(`Enqueuing next page: ${nextUrl}`);
                const absoluteUrl = nextUrl.startsWith('http') ? nextUrl : `https://www.finn.no${nextUrl}`;
                await crawler.addRequests([absoluteUrl]);
            }
        } else {
            log.info('No next page found or pagination ended.');
        }
    },
    // Let's handle failed requests
    failedRequestHandler({ request, log }) {
        log.error(`Request ${request.url} failed too many times.`);
    },
});

// Finn.no parameters:
// Read startUrls from Actor Input or default to our fallback
await crawler.addRequests(startUrls);

console.log(`Starting crawler pointing towards ${datasetName}...`);
await crawler.run();
console.log(`Crawler finished. Data is stored in Apify Actor Dataset: ${datasetName}`);

await Actor.exit();
