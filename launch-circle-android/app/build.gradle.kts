import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.plugin.compose")
}

val releaseSigningFile = rootProject.file("keystore.properties")
val releaseSigningProperties = Properties().apply {
    if (releaseSigningFile.isFile) {
        releaseSigningFile.inputStream().use(::load)
    }
}

android {
    namespace = "com.launchcircle.testers"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.launchcircle.testers"
        minSdk = 26
        targetSdk = 36
        versionCode = 2
        versionName = "1.0.1"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        val apiBaseUrl = providers.gradleProperty("launchCircleApiBaseUrl")
            .orElse("http://10.0.2.2:8000/")
            .get()
        val useDemoRepository = providers.gradleProperty("launchCircleUseDemoRepository")
            .orElse("true")
            .get()
            .toBoolean()
        val enableDevelopmentAuth = providers.gradleProperty("launchCircleEnableDevelopmentAuth")
            .orElse("false")
            .get()
            .toBoolean()
        val googleClientId = providers.gradleProperty("googleServerClientId")
            .orElse("CHANGE_ME.apps.googleusercontent.com")
            .get()
        buildConfigField("String", "API_BASE_URL", "\"$apiBaseUrl\"")
        buildConfigField("boolean", "USE_DEMO_REPOSITORY", useDemoRepository.toString())
        buildConfigField("boolean", "ENABLE_DEVELOPMENT_AUTH", enableDevelopmentAuth.toString())
        buildConfigField("String", "GOOGLE_SERVER_CLIENT_ID", "\"$googleClientId\"")
    }

    signingConfigs {
        if (releaseSigningFile.isFile) {
            create("release") {
                val configuredAlias = releaseSigningProperties.getProperty("keyAlias")
                require(configuredAlias == "launch-circle-upload") {
                    "Release signing keyAlias must be launch-circle-upload"
                }
                storeFile = rootProject.file(
                    requireNotNull(releaseSigningProperties.getProperty("storeFile")) {
                        "Missing storeFile in keystore.properties"
                    },
                )
                storePassword = requireNotNull(releaseSigningProperties.getProperty("storePassword")) {
                    "Missing storePassword in keystore.properties"
                }
                keyAlias = configuredAlias
                keyPassword = requireNotNull(releaseSigningProperties.getProperty("keyPassword")) {
                    "Missing keyPassword in keystore.properties"
                }
            }
        }
    }

    buildTypes {
        getByName("release") {
            // Release artifacts always use the HTTPS pilot backend and Google authentication.
            buildConfigField(
                "String",
                "API_BASE_URL",
                "\"https://launchcircle-api.duckdns.org/\"",
            )
            buildConfigField("boolean", "USE_DEMO_REPOSITORY", "false")
            buildConfigField("boolean", "ENABLE_DEVELOPMENT_AUTH", "false")
            buildConfigField(
                "String",
                "GOOGLE_SERVER_CLIENT_ID",
                "\"519813588502-4jlmnljs86ijr8kijmuesq6i147p5f0c.apps.googleusercontent.com\"",
            )
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
            if (releaseSigningFile.isFile) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2026.06.00")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.activity:activity-compose:1.13.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.11.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.11.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")

    implementation("androidx.credentials:credentials:1.6.0")
    implementation("androidx.credentials:credentials-play-services-auth:1.6.0")
    implementation("com.google.android.libraries.identity.googleid:googleid:1.2.0")

    implementation("com.squareup.retrofit2:retrofit:3.0.0")
    implementation("com.squareup.retrofit2:converter-gson:3.0.0")

    testImplementation("junit:junit:4.13.2")
}
