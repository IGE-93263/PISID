package com.maze;

import android.content.Context;
import android.os.Bundle;
import android.text.InputType;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AlertDialog;
import androidx.fragment.app.Fragment;

import org.json.JSONObject;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.FormBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

/**
 * Chama as stored procedures Criar_utilizador, Alterar_utilizador, Remover_utilizador,
 * Criar_jogo, Alterar_jogo via os PHP em /scripts/.
 */
public class AdminFragment extends Fragment {

    private static final String ARG_HOST = "host";
    private static final String ARG_DATABASE = "database";
    private static final String ARG_USERNAME = "username";
    private static final String ARG_PASSWORD = "password";
    private static final String ARG_TIPO = "tipo";

    private String host, database, username, password, tipo;
    private OkHttpClient client;

    public AdminFragment() {}

    public static AdminFragment newInstance(String host, String database, String username, String password, String tipo) {
        AdminFragment f = new AdminFragment();
        Bundle args = new Bundle();
        args.putString(ARG_HOST, host);
        args.putString(ARG_DATABASE, database);
        args.putString(ARG_USERNAME, username);
        args.putString(ARG_PASSWORD, password);
        args.putString(ARG_TIPO, tipo);
        f.setArguments(args);
        return f;
    }

    @Override
    public void onCreate(@Nullable Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (getArguments() != null) {
            host = getArguments().getString(ARG_HOST);
            database = getArguments().getString(ARG_DATABASE);
            username = getArguments().getString(ARG_USERNAME);
            password = getArguments().getString(ARG_PASSWORD);
            tipo = getArguments().getString(ARG_TIPO);
        }
        client = new OkHttpClient();
    }

    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View v = inflater.inflate(R.layout.fragment_admin, container, false);

        Button btnCriarUtilizador   = v.findViewById(R.id.btnCriarUtilizador);
        Button btnAlterarUtilizador = v.findViewById(R.id.btnAlterarUtilizador);
        Button btnRemoverUtilizador = v.findViewById(R.id.btnRemoverUtilizador);
        Button btnCriarJogo         = v.findViewById(R.id.btnCriarJogo);
        Button btnAlterarJogo       = v.findViewById(R.id.btnAlterarJogo);

        btnCriarUtilizador.setOnClickListener(b -> showCriarUtilizador());
        btnAlterarUtilizador.setOnClickListener(b -> showAlterarUtilizador());
        btnRemoverUtilizador.setOnClickListener(b -> showRemoverUtilizador());
        btnCriarJogo.setOnClickListener(b -> showCriarJogo());
        btnAlterarJogo.setOnClickListener(b -> showAlterarJogo());

        return v;
    }

    // ---------------- Diálogos ----------------

    private void showCriarUtilizador() {
        FieldSpec[] fields = {
                FieldSpec.intField("equipa", "Equipa (ID)"),
                FieldSpec.text("nome", "Nome"),
                FieldSpec.text("telemovel", "Telemóvel"),
                FieldSpec.text("tipo", "Tipo (ex: Aluno)"),
                FieldSpec.email("email", "Email"),
                FieldSpec.text("dataNascimento", "Data nascimento (YYYY-MM-DD)"),
        };
        showFormDialog("Criar utilizador", fields, "criar_utilizador.php");
    }

    private void showAlterarUtilizador() {
        FieldSpec[] fields = {
                FieldSpec.intField("idUtilizador", "ID utilizador"),
                FieldSpec.text("nome", "Nome"),
                FieldSpec.text("telemovel", "Telemóvel"),
                FieldSpec.text("tipo", "Tipo"),
                FieldSpec.email("email", "Email"),
                FieldSpec.text("dataNascimento", "Data nascimento (YYYY-MM-DD)"),
        };
        showFormDialog("Alterar utilizador", fields, "alterar_utilizador.php");
    }

    private void showRemoverUtilizador() {
        FieldSpec[] fields = {
                FieldSpec.intField("idUtilizador", "ID utilizador a remover"),
        };
        showFormDialog("Remover utilizador", fields, "remover_utilizador.php");
    }

    private void showCriarJogo() {
        FieldSpec[] fields = {
                FieldSpec.intField("idEquipa", "ID equipa"),
                FieldSpec.intField("idUtilizador", "ID utilizador"),
                FieldSpec.text("descricao", "Descrição"),
                FieldSpec.text("dataHoraInicio", "Início (YYYY-MM-DD HH:MM:SS,  = agora)"),
        };
        showFormDialog("Criar jogo", fields, "criar_jogo.php");
    }

    private void showAlterarJogo() {
        FieldSpec[] fields = {
                FieldSpec.intField("idSimulacao", "ID simulação"),
                FieldSpec.text("descricao", "Nova descrição"),
        };
        showFormDialog("Alterar jogo", fields, "alterar_jogo.php");
    }

    // ---------------- Builder genérico ----------------

    private void showFormDialog(String title, FieldSpec[] fields, String phpScript) {
        Context ctx = requireContext();
        LinearLayout root = new LinearLayout(ctx);
        root.setOrientation(LinearLayout.VERTICAL);
        int pad = (int) (16 * ctx.getResources().getDisplayMetrics().density);
        root.setPadding(pad, pad, pad, 0);

        Map<String, EditText> inputs = new LinkedHashMap<>();
        for (FieldSpec spec : fields) {
            EditText et = new EditText(ctx);
            et.setHint(spec.hint);
            et.setInputType(spec.inputType);
            root.addView(et);
            inputs.put(spec.name, et);
        }

        new AlertDialog.Builder(ctx)
                .setTitle(title)
                .setView(root)
                .setPositiveButton("Confirmar", (d, w) -> {
                    Map<String, String> values = new LinkedHashMap<>();
                    for (Map.Entry<String, EditText> e : inputs.entrySet()) {
                        values.put(e.getKey(), e.getValue().getText().toString().trim());
                    }
                    callSp(phpScript, values);
                })
                .setNegativeButton("Cancelar", null)
                .show();
    }

    // ---------------- Chamada HTTP ----------------

    private void callSp(String phpScript, Map<String, String> params) {
        FormBody.Builder fb = new FormBody.Builder()
                .add("username", username)
                .add("password", password)
                .add("database", database)
                // Tipo do utilizador autenticado — o PHP usa-o para escolher
                // se liga ao MySQL como admin_app (mais privilégios) ou user_app.
                .add("caller_tipo", tipo == null ? "" : tipo);
        for (Map.Entry<String, String> e : params.entrySet()) {
            fb.add(e.getKey(), e.getValue() == null ? "" : e.getValue());
        }
        RequestBody body = fb.build();

        Request request = new Request.Builder()
                .url("http://" + host + "/maze_app_php/" + phpScript)
                .post(body)
                .build();

        Log.d("AdminFragment", "POST -> " + request.url());

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(@NonNull Call call, @NonNull IOException e) {
                postToast("Erro de conexão: " + e.getMessage());
                Log.e("AdminFragment", "onFailure", e);
            }

            @Override
            public void onResponse(@NonNull Call call, @NonNull Response response) throws IOException {
                String responseBody = response.body() != null ? response.body().string() : "";
                Log.d("AdminFragment", "Resposta: " + responseBody);

                if (!response.isSuccessful()) {
                    showRawDialog("Erro HTTP " + response.code(), responseBody);
                    return;
                }
                try {
                    JSONObject json = new JSONObject(responseBody);
                    String msg = json.optString("message", "(sem mensagem)");
                    postToast(msg);
                } catch (Exception ex) {
                    // JSON inválido — mostra a resposta crua para debug
                    Log.e("AdminFragment", "JSON inválido: " + responseBody, ex);
                    showRawDialog("Resposta NÃO-JSON do servidor", responseBody);
                }
            }
        });
    }

    private void postToast(String msg) {
        if (getActivity() == null) return;
        getActivity().runOnUiThread(() ->
                Toast.makeText(getContext(), msg, Toast.LENGTH_LONG).show());
    }

    private void showRawDialog(String title, String body) {
        if (getActivity() == null) return;
        getActivity().runOnUiThread(() -> {
            // Mostra a resposta crua do servidor num diálogo selecionável
            android.widget.TextView tv = new android.widget.TextView(requireContext());
            tv.setText(body == null || body.isEmpty() ? "(resposta vazia)" : body);
            tv.setTextIsSelectable(true);
            int pad = (int) (16 * getResources().getDisplayMetrics().density);
            tv.setPadding(pad, pad, pad, pad);
            android.widget.ScrollView sv = new android.widget.ScrollView(requireContext());
            sv.addView(tv);
            new AlertDialog.Builder(requireContext())
                    .setTitle(title)
                    .setView(sv)
                    .setPositiveButton("OK", null)
                    .show();
        });
    }

    // ---------------- Helper para os campos ----------------

    private static class FieldSpec {
        final String name;
        final String hint;
        final int inputType;

        FieldSpec(String name, String hint, int inputType) {
            this.name = name;
            this.hint = hint;
            this.inputType = inputType;
        }

        static FieldSpec text(String name, String hint) {
            return new FieldSpec(name, hint, InputType.TYPE_CLASS_TEXT);
        }

        static FieldSpec intField(String name, String hint) {
            return new FieldSpec(name, hint, InputType.TYPE_CLASS_NUMBER);
        }

        static FieldSpec email(String name, String hint) {
            return new FieldSpec(name, hint,
                    InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        }
    }
}
