package com.launchcircle.testers.core.billing

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.PendingPurchasesParams
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.QueryPurchasesParams
import java.security.MessageDigest

class PlayBillingGateway(
    context: Context,
    private val onPurchaseToken: (String) -> Unit,
    private val onError: (String) -> Unit,
) {
    private var connected = false
    private var activeProductId: String? = null
    private val billingClient = BillingClient.newBuilder(context.applicationContext)
        .setListener(PurchasesUpdatedListener { result, purchases ->
            if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                purchases.orEmpty().filter { it.purchaseState == Purchase.PurchaseState.PURCHASED }
                    .forEach { purchase ->
                        if (activeProductId in purchase.products) {
                            onPurchaseToken(purchase.purchaseToken)
                        }
                    }
            } else if (result.responseCode != BillingClient.BillingResponseCode.USER_CANCELED) {
                onError(result.debugMessage.ifBlank { "Google Play purchase failed." })
            }
        })
        .enablePendingPurchases(PendingPurchasesParams.newBuilder().enableOneTimeProducts().build())
        .enableAutoServiceReconnection()
        .build()

    fun queryPrice(productId: String, onPrice: (String) -> Unit) {
        withConnection {
            queryProduct(productId) { details, offer -> onPrice(offer.formattedPrice) }
        }
    }

    fun launchPurchase(
        activity: Activity,
        productId: String,
        purchaseIntentId: String,
        onPrice: (String) -> Unit,
    ) {
        withConnection {
            queryProduct(productId) { details, offer ->
                onPrice(offer.formattedPrice)
                activeProductId = productId
                val productParams = BillingFlowParams.ProductDetailsParams.newBuilder()
                    .setProductDetails(details)
                    .setOfferToken(checkNotNull(offer.offerToken))
                    .build()
                val flow = BillingFlowParams.newBuilder()
                    .setProductDetailsParamsList(listOf(productParams))
                    .setObfuscatedAccountId(obfuscatedId(purchaseIntentId))
                    .build()
                val result = billingClient.launchBillingFlow(activity, flow)
                if (result.responseCode != BillingClient.BillingResponseCode.OK) {
                    onError(result.debugMessage.ifBlank { "Google Play could not open the purchase flow." })
                }
            }
        }
    }

    fun queryOwnedPurchase(productId: String, onToken: (String?) -> Unit) {
        withConnection {
            activeProductId = productId
            val params = QueryPurchasesParams.newBuilder()
                .setProductType(BillingClient.ProductType.INAPP)
                .build()
            billingClient.queryPurchasesAsync(params) { result, purchases ->
                if (result.responseCode != BillingClient.BillingResponseCode.OK) {
                    onError(result.debugMessage.ifBlank { "Google Play purchase status is unavailable." })
                    onToken(null)
                    return@queryPurchasesAsync
                }
                val ownedPurchase = purchases.firstOrNull { purchase ->
                    purchase.purchaseState == Purchase.PurchaseState.PURCHASED &&
                        productId in purchase.products
                }
                onToken(ownedPurchase?.purchaseToken)
            }
        }
    }

    fun close() {
        billingClient.endConnection()
    }

    private fun withConnection(action: () -> Unit) {
        if (connected) {
            action()
            return
        }
        billingClient.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(result: BillingResult) {
                if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                    connected = true
                    action()
                } else {
                    onError(result.debugMessage.ifBlank { "Google Play Billing is unavailable." })
                }
            }

            override fun onBillingServiceDisconnected() {
                connected = false
            }
        })
    }

    private fun queryProduct(productId: String, ready: (ProductDetails, ProductDetails.OneTimePurchaseOfferDetails) -> Unit) {
        val product = QueryProductDetailsParams.Product.newBuilder()
            .setProductId(productId)
            .setProductType(BillingClient.ProductType.INAPP)
            .build()
        val params = QueryProductDetailsParams.newBuilder().setProductList(listOf(product)).build()
        billingClient.queryProductDetailsAsync(params) { result, response ->
            val details = response.productDetailsList.firstOrNull { it.productId == productId }
            val offer = details?.oneTimePurchaseOfferDetailsList?.firstOrNull()
            if (result.responseCode == BillingClient.BillingResponseCode.OK && details != null && offer != null) {
                ready(details, offer)
            } else {
                onError("Google Play did not return a price for this product.")
            }
        }
    }

    private fun obfuscatedId(value: String): String = MessageDigest.getInstance("SHA-256")
        .digest("launch-circle:$value".toByteArray())
        .joinToString("") { "%02x".format(it) }
}
