export function Methodology() {
  return (
    <details className="group rounded-lg bg-[#fcfcfb] p-4 shadow-sm ring-1 ring-black/10">
      <summary className="cursor-pointer text-sm font-semibold text-stone-900 marker:text-stone-400">
        Methodology and assumptions
      </summary>
      <div className="mt-3 grid gap-4 text-sm leading-relaxed text-stone-700 md:grid-cols-2">
        <section>
          <h3 className="font-medium text-stone-900">What period is covered</h3>
          <p>
            Day-ahead purchases are decided the day before delivery. Decisions made from 1 to 31
            January 2026 therefore cover delivery days 2 January to 1 February 2026.
          </p>
        </section>
        <section>
          <h3 className="font-medium text-stone-900">Which forecast counts</h3>
          <p>
            In trading cutoff mode, each delivery hour uses the latest forecast published before
            the decision time on the previous day. The default, 09:50 UK time, is when the Nord
            Pool GB day-ahead auction closes. A forecast published even a minute later is never
            used. Fixed horizon mode instead uses the latest forecast made at least H hours before
            each delivery hour, to show how accuracy changes with lead time.
          </p>
        </section>
        <section>
          <h3 className="font-medium text-stone-900">Hourly forecasts, half-hourly actuals</h3>
          <p>
            Elexon publishes the wind forecast hourly and actual output every half hour. We score
            only the on-the-hour points where both exist, and never invent forecast values in
            between. Coverage shows how many hours were scored.
          </p>
        </section>
        <section>
          <h3 className="font-medium text-stone-900">Reading the error</h3>
          <p>
            Error is forecast minus actual. A positive error means wind came in below forecast,
            so you would have bought too little and had to cover the gap at short notice. That is
            the costly direction and is shown in red throughout.
          </p>
        </section>
        <section>
          <h3 className="font-medium text-stone-900">Why a P90 buffer, and not a percentage error</h3>
          <p>
            The shortfall buffer is the 90th percentile of error: buying that much above the
            forecast would have covered the shortfall in 9 out of 10 hours. We avoid percentage
            errors (MAPE) because wind output can be close to zero, where percentages become huge
            and misleading.
          </p>
        </section>
        <section>
          <h3 className="font-medium text-stone-900">Why forecasts run high</h3>
          <p>
            Over January the forecast was on average about 1.7 GW above actual output. The most
            likely reason is curtailment: the forecast estimates what wind farms could generate,
            while the actual figures are metered output after the grid operator turned some wind
            down. In practice, treat the forecast as a ceiling. The buffer already includes this
            systematic gap.
          </p>
        </section>
      </div>
      <p className="mt-4 text-xs text-stone-500">
        Data: Elexon BMRS, national level. Actuals from FUELHH (fuel type WIND), forecasts from
        WINDFOR. All times shown in UK time.
      </p>
    </details>
  )
}
