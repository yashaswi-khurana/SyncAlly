export const PAYPAL_INVOICE_CURRENCIES = [
  "AUD", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD",
  "HUF", "ILS", "JPY", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN", "RUB",
  "SEK", "SGD", "THB", "TWD", "USD",
] as const;

export const PAYPAL_INVOICE_CURRENCY_SET: ReadonlySet<string> = new Set(
  PAYPAL_INVOICE_CURRENCIES,
);
