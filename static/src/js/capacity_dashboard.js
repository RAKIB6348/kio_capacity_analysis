/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { getVendorBillDomain, loadVendorBillComparison } from "./vendor_bill_comparison";

const SELECTED_ITEM_STORAGE_KEY = "kio_capacity_selected_item";
const CURRENT_VIEW_STORAGE_KEY = "kio_capacity_current_view";

export class KioCapacityDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        const currentMonthRange = this.getCurrentMonthRange();
        const restoredState = this.getRestoredComparisonState();

        this.state = useState({
            loading: true,
            summary: {
                totalActiveCapacity: 0,
                totalSpend: 0,
                totalCapacityItems: 0,
            },
            capacityItems: [],
            currentView: restoredState ? "comparison" : "dashboard",
            dateFrom: restoredState ? restoredState.dateFrom : currentMonthRange.dateFrom,
            dateTo: restoredState ? restoredState.dateTo : currentMonthRange.dateTo,
            selectedItem: restoredState ? restoredState.selectedItem : null,
            comparisonLoading: false,
            vendorRows: [],
            comparisonSummary: {
                totalActiveCapacity: 0,
                totalCapacity: 0,
                totalPurchases: 0,
                totalSpend: 0,
                averagePrice: 0,
            },
        });

        onWillStart(async () => {
            if (this.state.currentView === "comparison" && this.state.selectedItem) {
                await this.loadVendorComparisonData();
            } else {
                await this.loadDashboardData();
            }
        });
    }

    getRestoredComparisonState() {
        const currentView = sessionStorage.getItem(CURRENT_VIEW_STORAGE_KEY);
        const savedItem = sessionStorage.getItem(SELECTED_ITEM_STORAGE_KEY);
        if (currentView !== "comparison" || !savedItem) {
            return null;
        }

        try {
            const parsedItem = JSON.parse(savedItem);
            const { dateFrom, dateTo, ...selectedItem } = parsedItem;

            if (!selectedItem || !selectedItem.itemId) {
                return null;
            }

            const currentMonthRange = this.getCurrentMonthRange();
            return {
                selectedItem,
                dateFrom: dateFrom || currentMonthRange.dateFrom,
                dateTo: dateTo || currentMonthRange.dateTo,
            };
        } catch (error) {
            console.error("Capacity Comparison Restore Error:", error);
            sessionStorage.removeItem(CURRENT_VIEW_STORAGE_KEY);
            sessionStorage.removeItem(SELECTED_ITEM_STORAGE_KEY);
            return null;
        }
    }

    saveComparisonState() {
        if (!this.state.selectedItem) {
            return;
        }

        sessionStorage.setItem(CURRENT_VIEW_STORAGE_KEY, "comparison");
        sessionStorage.setItem(
            SELECTED_ITEM_STORAGE_KEY,
            JSON.stringify({
                ...this.state.selectedItem,
                dateFrom: this.state.dateFrom,
                dateTo: this.state.dateTo,
            })
        );
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
                totalInvoiceAmount += amount;
            }

            const totalActiveCapacity = await this.orm.call(
                "kio.capacity.dashboard",
                "get_total_active_upstream_capacity",
                [],
                {
                    date_from: this.state.dateFrom || false,
                    date_to: this.state.dateTo || false,
                }
            );

            this.state.summary = {
                totalActiveCapacity,
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

    getCurrentMonthRange() {
        const today = new Date();
        const formatDate = (date) => {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, "0");
            const day = String(date.getDate()).padStart(2, "0");
            return `${year}-${month}-${day}`;
        };

        return {
            dateFrom: formatDate(new Date(today.getFullYear(), today.getMonth(), 1)),
            dateTo: formatDate(new Date(today.getFullYear(), today.getMonth() + 1, 0)),
        };
    }

    formatNumber(value) {
        return (value || 0).toLocaleString(undefined, {
            maximumFractionDigits: 2,
        });
    }

    async onDateRangeChange(field, value) {
        this.state[field] = value;
        if (this.state.selectedItem) {
            this.saveComparisonState();
            await this.loadVendorComparisonData();
        } else {
            await this.loadDashboardData();
        }
    }

    async clearDateRange() {
        const currentMonthRange = this.getCurrentMonthRange();
        this.state.dateFrom = currentMonthRange.dateFrom;
        this.state.dateTo = currentMonthRange.dateTo;
        if (this.state.selectedItem) {
            this.saveComparisonState();
            await this.loadVendorComparisonData();
        } else {
            await this.loadDashboardData();
        }
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

    getPurchaseDateDomain() {
        const domain = [];
        if (this.state.dateFrom) {
            domain.push(["purchase_date", ">=", this.state.dateFrom]);
        }
        if (this.state.dateTo) {
            domain.push(["purchase_date", "<=", this.state.dateTo]);
        }
        return domain;
    }

    getSelectedItemPurchaseDomain(vendorId = null) {
        const domain = [
            ["line_ids.capacity_item_id.name", "=", this.state.selectedItem.itemName],
            ...this.getPurchaseDateDomain(),
        ];
        if (vendorId) {
            domain.push(["provider_id", "=", vendorId]);
        }
        return domain;
    }

    getDisplayDate(value) {
        return value || "-";
    }

    getVendorAveragePrice(row) {
        return row.totalCapacity ? row.billAmount / row.totalCapacity : 0;
    }

    async openCapacityItemPurchases(item) {
        this.state.selectedItem = item;
        this.state.currentView = "comparison";
        this.saveComparisonState();
        await this.loadVendorComparisonData();
    }

    async backToDashboard() {
        sessionStorage.removeItem(CURRENT_VIEW_STORAGE_KEY);
        sessionStorage.removeItem(SELECTED_ITEM_STORAGE_KEY);
        this.state.currentView = "dashboard";
        this.state.selectedItem = null;
        this.state.vendorRows = [];
        this.state.comparisonSummary = {
            totalActiveCapacity: 0,
            totalCapacity: 0,
            totalPurchases: 0,
            totalSpend: 0,
            averagePrice: 0,
        };
        if (!this.state.capacityItems.length) {
            await this.loadDashboardData();
        }
    }

    async loadVendorComparisonData() {
        if (!this.state.selectedItem) {
            return;
        }

        this.state.comparisonLoading = true;

        try {
            const comparison = await loadVendorBillComparison(
                this.orm,
                this.state.selectedItem,
                this.state.dateFrom,
                this.state.dateTo
            );
            this.state.vendorRows = comparison.vendorRows;
            this.state.comparisonSummary = comparison.summary;
        } catch (error) {
            console.error("Vendor Bill Comparison Load Error:", error);
            this.state.vendorRows = [];
            this.state.comparisonSummary = {
                totalActiveCapacity: 0,
                totalCapacity: 0,
                totalPurchases: 0,
                totalSpend: 0,
                averagePrice: 0,
            };
        } finally {
            this.state.comparisonLoading = false;
        }
    }

    openVendorPurchases(row) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `${this.state.selectedItem.itemName} - ${row.vendorName} Vendor Bills`,
            res_model: "account.move",
            views: [
                [false, "tree"],
                [false, "form"],
            ],
            domain: getVendorBillDomain(
                this.state.selectedItem,
                this.state.dateFrom,
                this.state.dateTo,
                row.vendorId
            ),
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
