-- PostgreSQL schema for clients and transactions
-- Use this script to initialize the Supabase/PostgreSQL database.

-- 1. CLIENTS TABLE
CREATE TABLE IF NOT EXISTS public.clients (
    client_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    address VARCHAR(255) NULL,
    phone VARCHAR(20) NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- 2. TRANSACTIONS TABLE
CREATE TABLE IF NOT EXISTS public.transactions (
    transaction_id SERIAL PRIMARY KEY,
    client_id INT NOT NULL REFERENCES public.clients(client_id) ON DELETE CASCADE,
    order_id VARCHAR(50) UNIQUE NOT NULL,
    invoice_id VARCHAR(100) NULL,
    gateway_payment_id VARCHAR(50) NULL,
    gateway_signature VARCHAR(255) NULL,
    amount DECIMAL(10,2) NOT NULL,
    gross_amount DECIMAL(10,2) NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    status VARCHAR(20) DEFAULT 'Pending',
    short_url VARCHAR(255) NULL,
    invoice_path VARCHAR(255) NULL,
    payment_request_data JSONB NULL,
    payment_response_data JSONB NULL,
    after_payment_response_data JSONB NULL,
    coupon_code VARCHAR(50) DEFAULT 'NA',
    application_name VARCHAR(100) NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

CREATE INDEX IF NOT EXISTS idx_transactions_order_id ON public.transactions(order_id);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON public.transactions(status);
CREATE INDEX IF NOT EXISTS idx_clients_email ON public.clients(email);

-- 1. PROCEDURE: Create Transaction Order
CREATE OR REPLACE FUNCTION public.sp_create_transaction_order(
    p_name VARCHAR(100),
    p_email VARCHAR(100),
    p_address VARCHAR(255),
    p_amount DECIMAL(10,2),
    p_gross_amount DECIMAL(10,2),
    p_order_id VARCHAR(50),
    p_invoice_id VARCHAR(100),
    p_short_url VARCHAR(255),
    p_payment_request_data JSONB,
    p_payment_response_data JSONB,
    p_application_name VARCHAR(100),
    p_coupon_code VARCHAR(50)
)
RETURNS VOID AS $$
DECLARE
    v_client_id INT;
BEGIN
    SELECT client_id INTO v_client_id
    FROM public.clients
    WHERE email = p_email AND is_deleted = FALSE;

    IF v_client_id IS NULL THEN
        INSERT INTO public.clients (name, email, address)
        VALUES (p_name, p_email, p_address)
        RETURNING client_id INTO v_client_id;
    END IF;

    INSERT INTO public.transactions (
        client_id, order_id, invoice_id, amount, gross_amount,
        status, short_url, payment_request_data, payment_response_data,
        application_name, coupon_code
    )
    VALUES (
        v_client_id, p_order_id, p_invoice_id, p_amount, p_gross_amount,
        'issued', p_short_url, p_payment_request_data, p_payment_response_data,
        p_application_name, COALESCE(p_coupon_code, 'NA')
    );
END;
$$ LANGUAGE plpgsql;

-- 2. PROCEDURE: Update Transaction Success
CREATE OR REPLACE FUNCTION public.sp_update_transaction_success(
    p_order_id VARCHAR(50),
    p_gateway_payment_id VARCHAR(50),
    p_gateway_signature VARCHAR(255),
    p_invoice_path VARCHAR(255),
    p_after_payment_response_data JSONB
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE public.transactions
    SET
        gateway_payment_id = p_gateway_payment_id,
        gateway_signature = p_gateway_signature,
        status = 'Success',
        invoice_path = p_invoice_path,
        after_payment_response_data = p_after_payment_response_data,
        updated_at = CURRENT_TIMESTAMP
    WHERE order_id = p_order_id AND is_deleted = FALSE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No matching active transaction found for OrderId %', p_order_id;
    END IF;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- 3. PROCEDURE: Soft Delete Transaction
CREATE OR REPLACE FUNCTION public.sp_soft_delete_transaction(
    p_order_id VARCHAR(50)
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE public.transactions
    SET
        is_deleted = TRUE,
        deleted_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE order_id = p_order_id AND is_deleted = FALSE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No active transaction found to delete for OrderId %', p_order_id;
    END IF;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- 4. PROCEDURE: Soft Delete Client
CREATE OR REPLACE FUNCTION public.sp_soft_delete_client(
    p_client_id INT
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE public.clients
    SET
        is_deleted = TRUE,
        deleted_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE client_id = p_client_id AND is_deleted = FALSE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No active client found with ClientId %', p_client_id;
    END IF;

    UPDATE public.transactions
    SET
        is_deleted = TRUE,
        deleted_at = CURRENT_TIMESTAMP,
        updated_at = CURRENT_TIMESTAMP
    WHERE client_id = p_client_id AND is_deleted = FALSE;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- 5. PROCEDURE: Update Transaction Invoice
CREATE OR REPLACE FUNCTION public.sp_update_transaction_invoice(
    p_order_id VARCHAR(50),
    p_short_url VARCHAR(255),
    p_invoice_id VARCHAR(100)
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE public.transactions
    SET
        short_url = p_short_url,
        invoice_id = p_invoice_id,
        updated_at = CURRENT_TIMESTAMP
    WHERE order_id = p_order_id AND is_deleted = FALSE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No matching active transaction found for OrderId %', p_order_id;
    END IF;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- 6. PROCEDURE: Update Transaction Failed
CREATE OR REPLACE FUNCTION public.sp_update_transaction_failed(
    p_order_id VARCHAR(50),
    p_failure_reason VARCHAR(255)
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE public.transactions
    SET
        status = 'Failed',
        after_payment_response_data = jsonb_build_object('reason', p_failure_reason),
        updated_at = CURRENT_TIMESTAMP
    WHERE order_id = p_order_id AND is_deleted = FALSE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No active transaction found to update failed status for OrderId %', p_order_id;
    END IF;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;
