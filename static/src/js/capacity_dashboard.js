/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class KioCapacityDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            summary: {
                totalActiveCapacity: 0,
                totalSpend: 0,
                totalProviders: 0,
            },
            providers: [],
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        const purchases = await this.orm.searchRead(
            "kio.capacity.upstream.purchase",
            [],
            [
                "provider_id",
                "purchased_capacity",
                "price",
                "reference",
                "active",
                "responsible_user_id",
                "purchase_date",
            ],
            { context: { active_test: false } }
        );

        const providerMap = new Map();
        let totalActiveCapacity = 0;
        let totalSpend = 0;

        for (const purchase of purchases) {
            const providerId = purchase.provider_id ? purchase.provider_id[0] : false;
            const providerName = purchase.provider_id ? purchase.provider_id[1] : "No Provider";
            const mapKey = providerId || "no_provider";
            const capacity = purchase.purchased_capacity || 0;
            const price = purchase.price || 0;

            if (!providerMap.has(mapKey)) {
                providerMap.set(mapKey, {
                    providerId,
                    providerName,
                    totalCapacity: 0,
                    totalPrice: 0,
                    activeCount: 0,
                    totalCount: 0,
                });
            }

            const provider = providerMap.get(mapKey);
            provider.totalCapacity += capacity;
            provider.totalPrice += price;
            provider.totalCount += 1;

            if (purchase.active) {
                provider.activeCount += 1;
                totalActiveCapacity += capacity;
            }

            totalSpend += price;
        }

        this.state.summary = {
            totalActiveCapacity,
            totalSpend,
            totalProviders: providerMap.size,
        };
        this.state.providers = Array.from(providerMap.values()).sort((a, b) =>
            a.providerName.localeCompare(b.providerName)
        );
        this.state.loading = false;
    }

    formatNumber(value) {
        return (value || 0).toLocaleString(undefined, {
            maximumFractionDigits: 2,
        });
    }

    openProviderPurchases(provider) {
        const domain = provider.providerId
            ? [["provider_id", "=", provider.providerId]]
            : [["provider_id", "=", false]];

        this.action.doAction({
            type: "ir.actions.act_window",
            name: provider.providerName,
            res_model: "kio.capacity.upstream.purchase",
            views: [[false, "tree"], [false, "form"]],
            view_mode: "tree,form",
            domain,
            context: { active_test: false },
            target: "current",
        });
    }
}

KioCapacityDashboard.template = "kio_capacity_analysis.CapacityDashboard";

registry.category("actions").add("kio_capacity_analysis.capacity_dashboard", KioCapacityDashboard);
