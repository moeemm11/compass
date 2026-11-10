"use client";

import { useEffect, useState } from "react";
import { Card, Empty, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { money } from "@/lib/format";

export default function CommercialPage() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { api.get("/commercial").then(setItems); }, []);
  return (
    <div>
      <PageHeader title="Commercial assessments" subtitle="Estimated figures stay labelled as assumptions until someone marks them confirmed. No currency conversion is applied." />
      <div className="grid gap-3">
        {items.map((item) => (
          <Card key={item.id}>
            <p className="text-xs text-muted">{item.figures_label}</p>
            <div className="mt-2 grid gap-2 text-sm md:grid-cols-4">
              <span>Contract {money(item.contract_value, item.currency_code)}</span>
              <span>Cost {money(item.total_cost, item.currency_code)}</span>
              <span>Margin {item.gross_margin ?? "—"}%</span>
              <span>Expected contribution {money(item.expected_contribution, item.currency_code)}</span>
            </div>
          </Card>
        ))}
        {!items.length ? <Empty title="No commercial assessments" body="Add one from an opportunity workspace." /> : null}
      </div>
    </div>
  );
}
