plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.continuecontinue.anvilshell"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.continuecontinue.anvilshell"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0-checkpoint"
        testInstrumentationRunner = "android.app.InstrumentationTestRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    testOptions {
        unitTests.isReturnDefaultValues = true
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
