# Evaluating the discovery feed

The evaluation reads the current unfiltered prospect feed, including candidates whose stage is unknown. Portfolio references are excluded. It uses the feed’s priority order and breaks ties alphabetically. The returned ranked IDs show which records contributed to each result.

| Measure | Interpretation |
| --- | --- |
| Precision at 5 and 10 | The number accepted by an analyst divided by the cutoff. All positions must exist and each must currently have an explicit accept or reject decision. A watch, note or pending review leaves the value unknown. Reviewed records below the cutoff cannot fill a gap. |
| Population | Counts by stage and current review decision, plus counts of prospects with unknown funding or unverified registration. |
| Signal latency | Calendar days between the publisher’s date and the workspace’s earliest observation of that prospect on the same source URL. Several signals from one article count once per prospect. Missing, conflicting and reversed dates are counted separately. Historical captures contribute to this metric. |
| Duplicate review | Pairs flagged, pairs marked related or distinct, and the fraction of the queue reviewed. A related pair can represent two distinct affiliated ventures. Confirmed duplicate prevalence remains unknown. |
| Scan health | Successful live runs divided by successful, partial and failed live attempts. Replays and credential requirements have separate counts. Discard totals include eligibility filters, so a row-level parser error rate is unavailable. |

On 20 November 2026 a fresh replay of the bundled data produced 27 prospects, 541 excluded comparables and zero analyst decisions. Both precision values were therefore unknown. Of 30 prospect/source URL pairs, eight had usable publication and observation dates. Their median lag was 161.5 days, with a range of 24–252 days. Twenty-two pairs lacked dates. This retrospective sample provides no estimate of competitor discovery timing or overall recall.

## Assistant evidence assessment

On 20 November 2026 the assistant reviewed ten projects from [the recorded evidence bundle](../data/records.json) against public profiles. The sample covers award finalists and founder interviews. These judgments were made separately from the scoring rules and written only here. They supply no human precision labels.

| Project | Assessment and follow-up |
| --- | --- |
| IsoSphere Technologies | The team reports over 60 customer interviews and 14 letters of intent. A trade publication interviewed two named co-founders. Commercial interest warrants follow-up. The value of paid orders remains unknown. [TUM finalist profile](https://www.tum.de/en/innovation/entrepreneurship/news-events/tum-ideaward#c82356) · [CHEManager interview](https://chemanager-online.com/en/products/isosphere-technologies-fltmc-finalist-profile) |
| SOward | TUM uses “SOward” in its heading and “SO4ward” in the text about PFAS water treatment. Check both names when resolving its identity. The profile establishes finalist status. [TUM finalist profile](https://www.tum.de/en/innovation/entrepreneurship/news-events/tum-ideaward#c82358) |
| IARET Catalysis | The team describes recycling metals from used catalytic converters. Ask for a dated industrial trial before recording a customer pilot. [TUM finalist profile](https://www.tum.de/en/innovation/entrepreneurship/news-events/tum-ideaward#c82360) |
| AccessMRI | TUM says the team is integrating imaging components into a prototype. That supports development activity. Clinical deployment and purchasing evidence remain open. [TUM finalist profile](https://www.tum.de/en/innovation/entrepreneurship/news-events/tum-ideaward#c82357) |
| Sona8 | Y Combinator lists the software company, corroborating the recorded backing signal. The interview volume on its page is company-reported. Screen this as an already backed operating venture. [Y Combinator directory](https://www.ycombinator.com/companies/sona8) |
| EcoWeave | TUM calls the yarn-coating idea an early concept. Seek test results or a textile partner before crediting a working prototype or commercial demand. [TUM finalist profile](https://www.tum.de/en/innovation/entrepreneurship/news-events/tum-ideaward#c99430) |
| Charge Circle | In June, the founders described plans to incorporate in the third quarter. Their forward-looking statement supports founding intent at the time. A current registry entry is needed to update legal status. [KIT interview](https://kit-gruenderschmiede.de/grndung-des-monats-charge-circle/) |
| OnSite Solutions | The founders describe BAIOSS, a product for building operators, and report receiving EXIST support. The interview supports the team, product and grant claims. Equity financing and paid usage need separate evidence. [KIT FORGE interview](https://www.kit-forge.de/en/magazine/founder-of-the-month-onsite-solutions/) |
| marton.ai | The founders identify three complementary roles and report a Start-up BW Pre-Seed award with a co-investor. Verify investment terms and later financing before assigning a round or amount. [KIT FORGE interview](https://www.kit-forge.de/en/magazine/founder-of-the-month-marton-ai/) |
| data revolution | The founders reported customer contracts and self-financing when interviewed in May. The account supports early commercial activity. Subsequent financing remains open. [KIT interview](https://kit-gruenderschmiede.de/en/founder-of-the-month-data-revolution/) |
