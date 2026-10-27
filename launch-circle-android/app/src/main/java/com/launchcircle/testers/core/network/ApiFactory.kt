package com.launchcircle.testers.core.network

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiFactory {
    fun create(baseUrl: String): LaunchCircleApi = Retrofit.Builder()
        .baseUrl(baseUrl)
        .client(okhttp3.OkHttpClient.Builder().addInterceptor { chain ->
            val timed = if (chain.request().url.encodedPath.endsWith("/icon/google-play")) chain.withReadTimeout(60, java.util.concurrent.TimeUnit.SECONDS) else chain
            timed.proceed(chain.request())
        }.build())
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(LaunchCircleApi::class.java)
}
