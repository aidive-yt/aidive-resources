# One planted mutation per golden task: (task id, file, old, new)
MUTATIONS = {
  "money":      ("src/domain/money.ts", "if (value < min) {", "if (value <= min) {"),
  "customer":   ("src/domain/customer.ts", "name.trim() === \"\"", "name === \"\""),
  "invoice":    ("src/domain/invoice.ts", 'invoice.dueDate < now.toISOString()', 'invoice.dueDate <= now.toISOString()'),
  "validation": ("src/domain/validation.ts", "quantity < 1", "quantity < 0"),
  "migrations": ("src/store/migrations.ts", "{ customer: 0, invoice: 0, invoiceNumber: 0 }", "{ customer: 0, invoice: 0, invoiceNumber: 1 }"),
  "router":     ("src/http/router.ts", "decodeURIComponent(m[i + 1])", "m[i + 1]"),
}
