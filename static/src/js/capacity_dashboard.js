/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class KioCapacityDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        const today = new Date();
        const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
        const monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        const formatDate = (date) => date.toISOString().slice(0, 10);

        this.state = useState({
            loading: true,
            summary: {
                totalActiveCapacity: 0,
                totalSpend: 0,
                totalCapacityItems: 0,
            },
            capacityItems: [],
            dateFrom: formatDate(monthStart),
            dateTo: formatDate(monthEnd),
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;

        try {
            const invoiceLineDomain = [
                ["move_id.move_type", "=", "in_invoice"],
                ["move_id.state", "!=", "cancel"],
                ["display_type", "=", "product"],
            ];
            if (this.state.dateFrom) {
                invoiceLineDomain.push(["move_id.invoice_date", ">=", this.state.dateFrom]);
            }
            if (this.state.dateTo) {
                invoiceLineDomain.push(["move_id.invoice_date", "<=", this.state.dateTo]);
            }

            const serviceProducts = await this.orm.searchRead(
                "product.template",
                [
                    ["detailed_type", "=", "service"],
                    ["is_upstream_service", "=", true],
                ],
                ["id", "name", "active", "is_upstream_service"],
                { context: { active_test: false } }
            );

            const templateIds = serviceProducts.map((product) => product.id);
            const productVariants = templateIds.length
                ? await this.orm.searchRead(
                    "product.product",
                    [["product_tmpl_id", "in", templateIds]],
                    ["id", "product_tmpl_id"],
                    { context: { active_test: false } }
                )
                : [];

            const variantToTemplate = new Map();
            const templateToVariants = new Map();
            for (const variant of productVariants) {
                const templateId = variant.product_tmpl_id && variant.product_tmpl_id[0];
                if (!templateId) {
                    continue;
                }
                variantToTemplate.set(variant.id, templateId);
                if (!templateToVariants.has(templateId)) {
                    templateToVariants.set(templateId, []);
                }
                templateToVariants.get(templateId).push(variant.id);
            }

            const variantIds = productVariants.map((variant) => variant.id);
            if (variantIds.length) {
                invoiceLineDomain.push(["product_id", "in", variantIds]);
            } else {
                invoiceLineDomain.push(["id", "=", 0]);
            }

            const invoiceLines = await this.orm.searchRead(
                "account.move.line",
                invoiceLineDomain,
                [
                    "product_id",
                    "quantity",
                    "price_subtotal",
                    "move_id",
                    "partner_id",
                ],
                { context: { active_test: false } }
            );

            const itemMap = new Map();
            let totalSalesQuantity = 0;
            let totalInvoiceAmount = 0;

            for (const product of serviceProducts) {
                itemMap.set(product.id, {
                    itemId: product.id,
                    itemName: product.name,
                    active: product.active,
                    variantIds: templateToVariants.get(product.id) || [],
                    totalCapacity: 0,
                    totalPrice: 0,
                    purchaseCount: 0,
                });
            }

            for (const line of invoiceLines) {
                const variantId = line.product_id && line.product_id[0];
                const templateId = variantToTemplate.get(variantId);
                const item = itemMap.get(templateId);
                if (!item) {
                    continue;
                }

                const quantity = line.quantity || 0;
                const amount = line.price_subtotal || 0;

                item.totalCapacity += quantity;
                item.totalPrice += amount;
                item.purchaseCount += 1;
                totalSalesQuantity += quantity;
                totalInvoiceAmount += amount;
            }

            this.state.summary = {
                totalActiveCapacity: totalSalesQuantity,
                totalSpend: totalInvoiceAmount,
                totalCapacityItems: serviceProducts.length,
            };

            this.state.capacityItems = Array.from(itemMap.values()).sort((a, b) =>
                a.itemName.localeCompare(b.itemName)
            );
        } catch (error) {
            console.error("Dashboard Load Error:", error);
            this.state.capacityItems = [];
        } finally {
            this.state.loading = false;
        }
    }

    formatNumber(value) {
        return (value || 0).toLocaleString(undefined, {
            maximumFractionDigits: 2,
        });
    }

    async onDateRangeChange(field, value) {
        this.state[field] = value;
        await this.loadDashboardData();
    }

    async clearDateRange() {
        this.state.dateFrom = "";
        this.state.dateTo = "";
        await this.loadDashboardData();
    }

    getInvoiceLineDomain(item) {
        const domain = [
            ["move_id.move_type", "=", "in_invoice"],
            ["move_id.state", "!=", "cancel"],
            ["display_type", "=", "product"],
        ];
        if (item.variantIds && item.variantIds.length) {
            domain.push(["product_id", "in", item.variantIds]);
        } else {
            domain.push(["id", "=", 0]);
        }
        if (this.state.dateFrom) {
            domain.push(["move_id.invoice_date", ">=", this.state.dateFrom]);
        }
        if (this.state.dateTo) {
            domain.push(["move_id.invoice_date", "<=", this.state.dateTo]);
        }
        return domain;
    }

    openCapacityItemPurchases(item) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `${item.itemName} - Vendor Bill Lines`,
            res_model: "account.move.line",
            views: [
                [false, "tree"],
                [false, "form"],
            ],
            domain: this.getInvoiceLineDomain(item),
            context: { active_test: false },
            target: "current",
        });
    }

    openCapacityItemForm() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Create Upstream Service Product",
            res_model: "product.template",
            views: [[false, "form"]],
            context: {
                default_detailed_type: "service",
                default_is_upstream_service: true,
            },
            target: "current",
        });
    }
}

KioCapacityDashboard.template = "kio_capacity_analysis.CapacityDashboard";

registry
    .category("actions")
    .add("kio_capacity_analysis.capacity_dashboard", KioCapacityDashboard);