package com.launchcircle.testers.core.network

import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiFactory {
    fun create(baseUrl: String): LaunchCircleApi = Retrofit.Builder()
        .baseUrl(baseUrl)
        .client(okhttp3.OkHttpClient.Builder().addInterceptor { chain ->
            val request = chain.request().newBuilder()
                .header("X-Client-Version", com.launchcircle.testers.BuildConfig.VERSION_NAME)
                .header("X-Client-Platform", "android")
                .header("X-Device-Type", "mobile")
                .build()
            val timed = if (request.url.encodedPath.endsWith("/icon/google-play")) {
                chain.withReadTimeout(60, java.util.concurrent.TimeUnit.SECONDS)
            } else chain
            timed.proceed(request)
        }.build())
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(LaunchCircleApi::class.java)
}
