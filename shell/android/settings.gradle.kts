pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
        // HMS ML Kit 依赖所在仓库；默认构建不会解析它（见 app/build.gradle.kts 的 hmsAsr 开关）
        maven { url = uri("https://developer.huawei.com/repo/") }
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven { url = uri("https://developer.huawei.com/repo/") }
    }
}

rootProject.name = "HomecareShell"
include(":app")
