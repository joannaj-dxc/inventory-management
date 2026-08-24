<template>
  <div class="restocking-container">
    <h1>{{ t("restocking.title") }}</h1>

    <!-- Budget Section -->
    <div class="budget-section">
      <div class="budget-input-group">
        <label for="budget-slider">{{ t("restocking.budget") }}</label>
        <input
          id="budget-slider"
          v-model.number="currentBudget"
          type="range"
          min="0"
          max="10000"
          step="500"
          @change="handleBudgetChange"
          class="budget-slider"
        />
        <div class="budget-display">
          <span class="budget-value"
            >${{ currentBudget.toLocaleString() }}</span
          >
        </div>
      </div>

      <button
        @click="getRecommendations"
        :disabled="currentBudget <= 0 || loading"
        class="btn btn-primary"
      >
        {{
          loading ? t("restocking.loading") : t("restocking.getRecommendations")
        }}
      </button>
    </div>

    <!-- Budget Summary -->
    <div v-if="recommendations.length > 0" class="budget-summary">
      <div class="summary-card">
        <div class="summary-label">{{ t("restocking.budgetLabel") }}</div>
        <div class="summary-value">${{ currentBudget.toLocaleString() }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">{{ t("restocking.allocated") }}</div>
        <div class="summary-value">${{ totalAllocated.toLocaleString() }}</div>
      </div>
      <div class="summary-card">
        <div class="summary-label">{{ t("restocking.remaining") }}</div>
        <div class="summary-value">${{ budgetRemaining.toLocaleString() }}</div>
      </div>
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- Recommendations Table -->
    <div v-if="recommendations.length > 0" class="recommendations-section">
      <h2>{{ t("restocking.recommendations") }}</h2>
      <div class="table-wrapper">
        <table class="recommendations-table">
          <thead>
            <tr>
              <th class="checkbox-col">
                <input
                  type="checkbox"
                  v-model="selectAll"
                  @change="toggleSelectAll"
                  class="select-all-checkbox"
                />
              </th>
              <th>{{ t("restocking.sku") }}</th>
              <th>{{ t("restocking.name") }}</th>
              <th>{{ t("restocking.category") }}</th>
              <th>{{ t("restocking.unitCost") }}</th>
              <th>{{ t("restocking.currentQty") }}</th>
              <th>{{ t("restocking.forecastedQty") }}</th>
              <th>{{ t("restocking.recommendedQty") }}</th>
              <th>{{ t("restocking.totalCost") }}</th>
              <th>{{ t("restocking.priority") }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in recommendations"
              :key="item.sku"
              :class="[
                'priority-' + item.priority,
                { selected: selectedItems.includes(item.sku) },
              ]"
            >
              <td class="checkbox-col">
                <input
                  type="checkbox"
                  :value="item.sku"
                  v-model="selectedItems"
                  class="item-checkbox"
                />
              </td>
              <td>
                <strong>{{ item.sku }}</strong>
              </td>
              <td>{{ item.name }}</td>
              <td>{{ item.category }}</td>
              <td>${{ item.unit_cost.toFixed(2) }}</td>
              <td>{{ item.current_quantity }}</td>
              <td>{{ item.forecasted_demand }}</td>
              <td>{{ item.recommended_quantity }}</td>
              <td>${{ item.total_cost.toFixed(2) }}</td>
              <td>
                <span :class="'priority-badge priority-' + item.priority">
                  {{ item.priority }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- No Recommendations State -->
    <div v-else-if="!loading && showNoResults" class="no-results">
      <p>{{ t("restocking.noRecommendations") }}</p>
    </div>

    <!-- Place Order Section -->
    <div v-if="selectedItems.length > 0" class="place-order-section">
      <div class="order-summary">
        <h3>{{ t("restocking.orderSummary") }}</h3>
        <div class="summary-stats">
          <div class="stat">
            <span class="label">{{ t("restocking.selectedItems") }}:</span>
            <span class="value">{{ selectedItems.length }}</span>
          </div>
          <div class="stat">
            <span class="label">{{ t("restocking.orderTotal") }}:</span>
            <span class="value"
              >${{
                selectedOrderTotal.toLocaleString("en-US", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })
              }}</span
            >
          </div>
        </div>
      </div>

      <button
        @click="placeOrder"
        :disabled="submitting"
        class="btn btn-success"
      >
        {{
          submitting ? t("restocking.submitting") : t("restocking.placeOrder")
        }}
      </button>
    </div>

    <!-- Success Message -->
    <div v-if="successMessage" class="success-message">
      <p>{{ successMessage }}</p>
      <button @click="resetForm" class="btn btn-secondary">
        {{ t("restocking.placeAnotherOrder") }}
      </button>
    </div>
  </div>
</template>

<script>
import { ref, computed } from "vue";
import { useI18n } from "../composables/useI18n";
import { api } from "../api";

export default {
  name: "Restocking",
  setup() {
    const { t } = useI18n();
    const currentBudget = ref(5000);
    const loading = ref(false);
    const submitting = ref(false);
    const error = ref(null);
    const successMessage = ref(null);
    const recommendations = ref([]);
    const selectedItems = ref([]);
    const selectAll = ref(false);
    const showNoResults = ref(false);

    const totalAllocated = computed(() => {
      if (recommendations.value.length === 0) return 0;
      return recommendations.value.reduce(
        (sum, item) => sum + item.total_cost,
        0,
      );
    });

    const budgetRemaining = computed(() => {
      return currentBudget.value - totalAllocated.value;
    });

    const selectedOrderTotal = computed(() => {
      return recommendations.value
        .filter((item) => selectedItems.value.includes(item.sku))
        .reduce((sum, item) => sum + item.total_cost, 0);
    });

    const handleBudgetChange = () => {
      recommendations.value = [];
      selectedItems.value = [];
      selectAll.value = false;
      showNoResults.value = false;
    };

    const getRecommendations = async () => {
      error.value = null;
      successMessage.value = null;
      loading.value = true;
      showNoResults.value = false;

      try {
        const response = await api.getRestockingRecommendations(
          currentBudget.value,
        );
        recommendations.value = response.recommendations || [];
        selectedItems.value = [];
        selectAll.value = false;
        showNoResults.value = recommendations.value.length === 0;
      } catch (err) {
        error.value =
          t("restocking.errorLoadingRecommendations") + ": " + err.message;
      } finally {
        loading.value = false;
      }
    };

    const toggleSelectAll = () => {
      if (selectAll.value) {
        selectedItems.value = recommendations.value.map((item) => item.sku);
      } else {
        selectedItems.value = [];
      }
    };

    const placeOrder = async () => {
      if (selectedItems.value.length === 0) {
        error.value = t("restocking.selectItemsError");
        return;
      }

      submitting.value = true;
      error.value = null;

      try {
        const selectedRecommendations = recommendations.value.filter((item) =>
          selectedItems.value.includes(item.sku),
        );

        const orderItems = selectedRecommendations.map((item) => ({
          sku: item.sku,
          name: item.name,
          quantity: item.recommended_quantity,
          unit_cost: item.unit_cost,
          category: item.category,
        }));

        const response = await api.submitRestockingOrder(
          orderItems,
          selectedOrderTotal.value,
        );

        if (response) {
          successMessage.value =
            t("restocking.orderSuccess") + " " + response.order_number;
        }
      } catch (err) {
        error.value = t("restocking.errorPlacingOrder") + ": " + err.message;
      } finally {
        submitting.value = false;
      }
    };

    const resetForm = () => {
      currentBudget.value = 5000;
      recommendations.value = [];
      selectedItems.value = [];
      selectAll.value = false;
      successMessage.value = null;
      error.value = null;
      showNoResults.value = false;
    };

    return {
      t,
      currentBudget,
      loading,
      submitting,
      error,
      successMessage,
      recommendations,
      selectedItems,
      selectAll,
      totalAllocated,
      budgetRemaining,
      selectedOrderTotal,
      showNoResults,
      handleBudgetChange,
      getRecommendations,
      toggleSelectAll,
      placeOrder,
      resetForm,
    };
  },
};
</script>

<style scoped>
.restocking-container {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

h1 {
  color: #1e3c72;
  margin-bottom: 24px;
  font-size: 2em;
}

h2 {
  color: #2a5298;
  margin-top: 24px;
  margin-bottom: 16px;
  font-size: 1.5em;
}

h3 {
  color: #2a5298;
  font-size: 1.1em;
  margin-bottom: 12px;
}

/* Budget Section */
.budget-section {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 24px;
  border: 1px solid #e0e4e8;
}

.budget-input-group {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 16px;
}

.budget-input-group label {
  font-weight: 600;
  color: #1e3c72;
  min-width: 150px;
}

.budget-slider {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: #e0e4e8;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2a5298;
  cursor: pointer;
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2a5298;
  cursor: pointer;
  border: none;
}

.budget-display {
  min-width: 120px;
  text-align: right;
}

.budget-value {
  font-size: 1.2em;
  font-weight: 600;
  color: #2a5298;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 1em;
}

.btn-primary {
  background: #2a5298;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1e3c72;
  box-shadow: 0 4px 12px rgba(42, 82, 152, 0.3);
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-success {
  background: #28a745;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #218838;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.btn-secondary:hover {
  background: #5a6268;
}

/* Budget Summary */
.budget-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.summary-card {
  background: white;
  border: 2px solid #e0e4e8;
  padding: 16px;
  border-radius: 8px;
  text-align: center;
}

.summary-label {
  color: #666;
  font-size: 0.9em;
  margin-bottom: 8px;
}

.summary-value {
  font-size: 1.5em;
  font-weight: 700;
  color: #2a5298;
}

/* Messages */
.error-message {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 16px;
}

.success-message {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
  padding: 16px;
  border-radius: 6px;
  margin-bottom: 16px;
}

.success-message p {
  margin: 0 0 12px 0;
}

.no-results {
  text-align: center;
  padding: 40px;
  color: #666;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 24px;
}

/* Recommendations Table */
.recommendations-section {
  margin-bottom: 24px;
}

.table-wrapper {
  overflow-x: auto;
  border: 1px solid #e0e4e8;
  border-radius: 8px;
}

.recommendations-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
}

.recommendations-table thead {
  background: #1e3c72;
  color: white;
}

.recommendations-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid #2a5298;
}

.recommendations-table td {
  padding: 12px;
  border-bottom: 1px solid #e0e4e8;
}

.recommendations-table tbody tr:hover {
  background: #f8f9fa;
}

.recommendations-table tbody tr.selected {
  background: #e8f4f8;
}

.checkbox-col {
  width: 40px;
  text-align: center;
}

.select-all-checkbox,
.item-checkbox {
  cursor: pointer;
  width: 18px;
  height: 18px;
}

.priority-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85em;
  font-weight: 600;
  text-transform: capitalize;
}

.priority-urgent {
  background: #f8d7da;
  color: #721c24;
}

.priority-high {
  background: #fff3cd;
  color: #856404;
}

.priority-medium {
  background: #d1ecf1;
  color: #0c5460;
}

.recommendations-table tbody tr.priority-urgent {
  border-left: 4px solid #dc3545;
}

.recommendations-table tbody tr.priority-high {
  border-left: 4px solid #ffc107;
}

.recommendations-table tbody tr.priority-medium {
  border-left: 4px solid #17a2b8;
}

/* Place Order Section */
.place-order-section {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border: 2px solid #2a5298;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
}

.order-summary {
  flex: 1;
}

.summary-stats {
  display: flex;
  gap: 30px;
  margin-top: 12px;
}

.stat {
  display: flex;
  gap: 10px;
  align-items: center;
}

.stat .label {
  font-weight: 600;
  color: #1e3c72;
}

.stat .value {
  font-size: 1.2em;
  font-weight: 700;
  color: #2a5298;
}

@media (max-width: 768px) {
  .budget-input-group {
    flex-direction: column;
    align-items: flex-start;
  }

  .place-order-section {
    flex-direction: column;
    align-items: stretch;
  }

  .summary-stats {
    flex-direction: column;
    gap: 12px;
  }

  .recommendations-table {
    font-size: 0.9em;
  }

  .recommendations-table th,
  .recommendations-table td {
    padding: 8px;
  }
}
</style>
