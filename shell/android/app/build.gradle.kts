plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.family.eldercare.screen"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.family.eldercare.screen"
        minSdk = 26
        targetSdk = 33
        versionCode = 1
        versionName = "0.1.0"

        // 壳版本：与 /workspace/shell/version.json、/api/version 的 min_shell_version 对齐
        buildConfigField("String", "SHELL_VERSION", "\"0.1.0\"")
        // Web 入口：业务页面全部由服务端下发，壳只负责原生能力
        buildConfigField("String", "SERVER_URL", "\"https://homecare.cinnamon.xin/\"")
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
        }
        release {
            isMinifyEnabled = false
            // 正式签名使用本地 keystore，不提交仓库；见 docs/stage4-handoff.md
        }
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    // 刻意不引入 androidx：壳只有一个 Activity + WebView，依赖越少构建越稳
}
