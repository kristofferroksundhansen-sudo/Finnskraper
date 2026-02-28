import { PlaywrightCrawler, Dataset } from 'crawlee';

// We use ES module syntax. We'll rename this to main.mjs or add "type": "module" to package.json.

const crawler = new PlaywrightCrawler({
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

        // Filter and clean the data
        for (const item of listings) {
            if (item.title && item.url) {
                // Ensure it's a Nissan Leaf (just to be safe) and we also record the location
                await Dataset.pushData(item);
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
// make=0.792 (Nissan) -> This is an example, let's just use the query parameter 'q=Nissan+Leaf' for safety.
// location=0.20061 (Oslo), location=1.20061.20507 or similar for Vestfold.
// To avoid guessing IDs, we can just use the query and perhaps region filters if we know them, 
// or let the user provide the exact search URL. 
// For now, let's start with a general query.
const START_URL = 'https://www.finn.no/car/used/search.html?q=Nissan+Leaf';

await crawler.addRequests([START_URL]);

console.log('Starting crawler...');
await crawler.run();
console.log('Crawler finished. Data is stored in ./storage/datasets/default');
