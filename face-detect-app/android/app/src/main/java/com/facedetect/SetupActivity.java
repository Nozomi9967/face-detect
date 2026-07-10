package com.facedetect;

import android.Manifest;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.zxing.ResultPoint;
import com.journeyapps.barcodescanner.BarcodeCallback;
import com.journeyapps.barcodescanner.BarcodeResult;
import com.journeyapps.barcodescanner.BarcodeView;

import java.net.HttpURLConnection;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.URL;
import java.util.Enumeration;

/**
 * SetupActivity — 配网页面
 *
 * 三种方式连接：
 * 1. 自动扫描网络发现后端
 * 2. 扫码（扫描电脑屏幕上 /setup 页面的二维码）
 * 3. 手动输入地址
 */
public class SetupActivity extends AppCompatActivity {

    private EditText serverUrlInput;
    private TextView discoveredText;
    private TextView statusText;
    private Button connectBtn;
    private Button scanBtn;

    private static final String PREFS_NAME = "FaceDetectPrefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final String KEY_HAS_CONFIGURED = "has_configured";
    private static final int PORT = 8000;
    private static final int CAMERA_REQUEST_CODE = 2001;

    private static final String[] SUBNETS = {
            "192.168.43.", "192.168.1.", "192.168.0.",
            "192.168.137.", "192.168.31.", "10.0.2.2",
            "192.168.95.", "192.168.172.", "172.30.",
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_setup);

        serverUrlInput = findViewById(R.id.server_url_input);
        discoveredText = findViewById(R.id.discovered_text);
        statusText = findViewById(R.id.status_text);
        connectBtn = findViewById(R.id.connect_btn);
        scanBtn = findViewById(R.id.scan_btn);
        Button cancelBtn = findViewById(R.id.cancel_btn);

        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        String savedUrl = prefs.getString(KEY_SERVER_URL, "");
        if (!savedUrl.isEmpty()) {
            serverUrlInput.setText(savedUrl);
        }

        if (prefs.getBoolean(KEY_HAS_CONFIGURED, false) && !savedUrl.isEmpty()) {
            autoConnect(savedUrl);
            return;
        }

        cancelBtn.setOnClickListener(v -> finish());
        connectBtn.setOnClickListener(v -> attemptConnect());
        scanBtn.setOnClickListener(v -> startQRScan());
        new ScanNetworkTask().execute();
    }

    // ── QR 扫码 ────────────────────────────────────────────

    private void startQRScan() {
        if (!hasCameraPermission()) {
            requestCameraPermission();
            return;
        }
        launchScanner();
    }

    private boolean hasCameraPermission() {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED;
    }

    private void requestCameraPermission() {
        ActivityCompat.requestPermissions(this,
                new String[]{Manifest.permission.CAMERA}, CAMERA_REQUEST_CODE);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode,
                                           @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == CAMERA_REQUEST_CODE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                launchScanner();
            } else {
                if (ActivityCompat.shouldShowRequestPermissionRationale(this,
                        Manifest.permission.CAMERA)) {
                    Toast.makeText(this, "需要相机权限才能扫码", Toast.LENGTH_SHORT).show();
                } else {
                    showPermissionDeniedDialog();
                }
            }
        }
    }

    private void showPermissionDeniedDialog() {
        new AlertDialog.Builder(this)
                .setTitle("需要相机权限")
                .setMessage("请在系统设置中允许 FaceDetect 使用相机，然后重试。")
                .setPositiveButton("去设置", (d, w) -> {
                    Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                    intent.setData(Uri.fromParts("package", getPackageName(), null));
                    startActivity(intent);
                })
                .setNegativeButton("取消", null)
                .show();
    }

    private void launchScanner() {
        try {
            BarcodeView barcodeView = new BarcodeView(this);

            FrameLayout container = new FrameLayout(this);
            container.addView(barcodeView,
                    new FrameLayout.LayoutParams(
                            FrameLayout.LayoutParams.MATCH_PARENT,
                            FrameLayout.LayoutParams.MATCH_PARENT));

            AlertDialog dialog = new AlertDialog.Builder(this)
                    .setTitle("扫描二维码")
                    .setMessage("将摄像头对准电脑屏幕上的二维码")
                    .setCancelable(true)
                    .create();
            dialog.setView(container);

            barcodeView.decodeContinuous(new BarcodeCallback() {
                @Override
                public void barcodeResult(BarcodeResult result) {
                    if (result.getText() != null && !result.getText().isEmpty()) {
                        barcodeView.pause();
                        dialog.dismiss();
                        String scanned = result.getText().trim();
                        runOnUiThread(() -> handleScannedUrl(scanned));
                    }
                }

                @Override
                public void possibleResultPoints(
                        java.util.List<ResultPoint> resultPoints) {
                    // no-op
                }
            });

            dialog.setOnDismissListener(d -> barcodeView.pause());
            dialog.show();

            new Handler(Looper.getMainLooper()).postDelayed(barcodeView::resume, 500);
        } catch (Exception e) {
            Toast.makeText(this, "无法启动扫码，请使用手动输入", Toast.LENGTH_SHORT).show();
        }
    }

    private void handleScannedUrl(String scanned) {
        String url = scanned.trim();
        if (url.startsWith("http://") || url.startsWith("https://")) {
            serverUrlInput.setText(url);
        } else {
            if (url.contains(":") && !url.contains("http")) {
                url = "http://" + url;
            } else if (!url.contains(":")) {
                url = "http://" + url + ":8000/";
            }
            serverUrlInput.setText(url);
        }
        statusText.setText("已扫码，地址已填入");
        statusText.setTextColor(getResources().getColor(R.color.text_secondary));
        attemptConnect();
    }

    // ── 自动连接 ───────────────────────────────────────────

    private void autoConnect(String url) {
        statusText.setText("正在连接已保存的服务器...");
        connectBtn.setEnabled(false);
        scanBtn.setEnabled(false);
        new VerifyTask(url).execute(url);
    }

    // ── 网络扫描 ───────────────────────────────────────────

    private class ScanNetworkTask extends AsyncTask<Void, String, String> {
        @Override
        protected String doInBackground(Void... voids) {
            StringBuilder result = new StringBuilder();
            result.append("本机 IP: ").append(getLocalIp()).append("\n");
            String foundIp = null;

            for (String subnet : SUBNETS) {
                if (isCancelled()) break;
                publishProgress("扫描 " + subnet + "x ...");
                foundIp = scanSubnet(subnet, 50);
                if (foundIp != null) break;
            }

            if (foundIp == null) {
                String localIp = getLocalIp();
                if (localIp != null && !localIp.startsWith("127.")) {
                    int lastDot = localIp.lastIndexOf('.');
                    if (lastDot > 0) {
                        String subnet = localIp.substring(0, lastDot + 1);
                        publishProgress("扫描本机网段 " + subnet + "x ...");
                        foundIp = scanSubnet(subnet, 30);
                    }
                }
            }

            if (foundIp != null) {
                result.append("发现服务器: ").append(foundIp).append(":").append(PORT);
            } else {
                result.append("未自动发现服务器，请扫码或手动输入");
            }
            return result.toString();
        }

        @Override
        protected void onProgressUpdate(String... values) {
            statusText.setText(values[0]);
        }

        @Override
        protected void onPostExecute(String result) {
            discoveredText.setText(result);
            String found = extractIp(result);
            if (found != null) {
                serverUrlInput.setText("http://" + found + ":" + PORT + "/");
            }
        }
    }

    // ── 验证连接 ───────────────────────────────────────────

    private class VerifyTask extends AsyncTask<String, Void, Boolean> {
        private String testUrl;

        VerifyTask(String url) {
            this.testUrl = url.endsWith("/") ? url : url + "/";
        }

        @Override
        protected Boolean doInBackground(String... urls) {
            try {
                URL url = new URL(testUrl + "api/health");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setConnectTimeout(3000);
                conn.setReadTimeout(3000);
                conn.setRequestMethod("GET");
                int code = conn.getResponseCode();
                conn.disconnect();
                return code == 200;
            } catch (Exception e) {
                return false;
            }
        }

        @Override
        protected void onPostExecute(Boolean success) {
            if (success) {
                saveAndProceed(testUrl);
            } else {
                statusText.setText("连接失败，请检查地址后重试");
                statusText.setTextColor(getResources().getColor(R.color.error));
                connectBtn.setEnabled(true);
                scanBtn.setEnabled(true);
            }
        }
    }

    private void attemptConnect() {
        String url = serverUrlInput.getText().toString().trim();
        if (url.isEmpty()) {
            Toast.makeText(this, "请输入服务器地址", Toast.LENGTH_SHORT).show();
            return;
        }
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://" + url;
        }
        if (!url.endsWith("/")) url += "/";

        statusText.setText("正在连接 " + url + " ...");
        statusText.setTextColor(getResources().getColor(R.color.text_secondary));
        connectBtn.setEnabled(false);
        scanBtn.setEnabled(false);
        new VerifyTask(url).execute(url);
    }

    private void saveAndProceed(String url) {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit()
                .putString(KEY_SERVER_URL, url)
                .putBoolean(KEY_HAS_CONFIGURED, true)
                .apply();

        statusText.setText("连接成功！正在进入...");
        statusText.setTextColor(getResources().getColor(R.color.success));

        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            startActivity(new Intent(SetupActivity.this, MainActivity.class));
            finish();
        }, 500);
    }

    // ── 网络辅助 ───────────────────────────────────────────

    private static String getLocalIp() {
        try {
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            while (interfaces.hasMoreElements()) {
                NetworkInterface iface = interfaces.nextElement();
                if (iface.isLoopback() || !iface.isUp()) continue;
                Enumeration<InetAddress> addrs = iface.getInetAddresses();
                while (addrs.hasMoreElements()) {
                    InetAddress addr = addrs.nextElement();
                    String ip = addr.getHostAddress();
                    if (ip != null && ip.contains(".") && !ip.contains(":")) {
                        return ip;
                    }
                }
            }
        } catch (Exception e) {
            // ignore
        }
        return "127.0.0.1";
    }

    private String scanSubnet(String subnet, int timeoutMs) {
        long deadline = System.currentTimeMillis() + timeoutMs;
        for (int i = 1; i < 255; i++) {
            if (System.currentTimeMillis() > deadline) break;
            String host = subnet + i;
            if (isHostReachable(host, 300) && isServiceRunning(host)) {
                return host;
            }
        }
        return null;
    }

    private boolean isHostReachable(String ip, int timeoutMs) {
        try {
            return InetAddress.getByName(ip).isReachable(timeoutMs);
        } catch (Exception e) {
            return false;
        }
    }

    private boolean isServiceRunning(String ip) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL("http://" + ip + ":" + PORT + "/api/health");
            conn = (HttpURLConnection) url.openConnection();
            conn.setConnectTimeout(500);
            conn.setReadTimeout(500);
            conn.setRequestMethod("GET");
            return conn.getResponseCode() == 200;
        } catch (Exception e) {
            return false;
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    private String extractIp(String text) {
        for (String line : text.split("\n")) {
            if (line.contains("http://")) {
                int start = line.indexOf("http://") + 7;
                int end = line.indexOf(":", start);
                if (end > start) {
                    return line.substring(start, end);
                }
            }
        }
        return null;
    }
}
